pipeline {
    agent any
    
    environment {
        APP_NAME = 'automarkly-frontend'
        BUILD_NUMBER = "${env.BUILD_NUMBER}"
        AWS_REGION = 'ap-south-1'
        TEST_EMAIL = 'sara.beck.dev@gmail.com'
        
        S3_BUCKET = credentials('s3-static-bucket')
        CLOUDFRONT_DISTRIBUTION_ID = credentials('cloudfront-distribution-id')
        CLOUDFRONT_DOMAIN = credentials('cloudfront-domain')
    }

    triggers {
        githubPush()
    }
    
    stages {
        stage('Checkout') {
            when {
                anyOf {
                    branch 'main'
                    branch 'feature/*'
                    branch 'release/*'
                }
            }
            steps {
                checkout scm
                sshagent(['github']) {
                    sh "git fetch --tags --unshallow || git fetch --tags"
                }
            }
        }
        
        stage('Unit Tests') {
            when {
                anyOf {
                    branch 'main'
                    branch 'feature/*'
                    branch 'release/*'
                }
            }
            steps {
                sh '''
                    docker build -f Dockerfile.test -t "${APP_NAME}:test-${BUILD_NUMBER}" .
                    mkdir -p test-results
                    docker run --rm \
                        -v "${PWD}/test-results:/app/test-results" \
                        "${APP_NAME}:test-${BUILD_NUMBER}"
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'test-results/**/*', allowEmptyArchive: true
                    sh 'docker rmi "${APP_NAME}:test-${BUILD_NUMBER}" || true'
                }
            }
        }
        
        stage('Build Images') {
            when {
                anyOf {
                    branch 'main'
                    branch 'feature/*'
                    branch 'release/*'
                }
            }
            parallel {
                stage('Build Static Files') {
                    steps {
                        sh '''
                            docker build --target artifacts -t "${APP_NAME}:artifacts-${BUILD_NUMBER}" .
                            CONTAINER_ID=$(docker create "${APP_NAME}:artifacts-${BUILD_NUMBER}")
                            rm -rf build
                            docker cp "${CONTAINER_ID}:/build" ./build
                            docker rm "${CONTAINER_ID}"
                            
                            if [ ! -d "build/static" ]; then
                                echo "Build verification failed"
                                exit 1
                            fi
                        '''
                    }
                    post {
                        always {
                            sh 'docker rmi "${APP_NAME}:artifacts-${BUILD_NUMBER}" || true'
                        }
                    }
                }
                
                stage('Build E2E Image') {
                    steps {
                        sh '''
                            docker build --target nginx -t "frontend-e2e:${BUILD_NUMBER}" .
                        '''
                    }
                }
            }
        }
        
        stage('Run E2E Tests') {
            when {
                anyOf {
                    branch 'main'
                    branch 'feature/*'
                    branch 'release/*'
                }
            }
            steps {
                withCredentials([
                    string(credentialsId: 'aws-account-id', variable: 'AWS_ID'),
                    string(credentialsId: 'aws_region', variable: 'REGION')
                ]) {
                    script {
                        def e2eResult = build job: 'e2e-email-service',
                              parameters: [
                                  string(name: 'BACKEND_IMAGE', value: "${AWS_ID}.dkr.ecr.${REGION}.amazonaws.com/automarkly/emailservice-backend:latest"),
                                  string(name: 'FRONTEND_IMAGE', value: "frontend-e2e:${BUILD_NUMBER}"),
                                  string(name: 'WORKER_IMAGE', value: "${AWS_ID}.dkr.ecr.${REGION}.amazonaws.com/automarkly/emailservice-worker:latest")
                              ],
                              wait: true,
                              propagate: false
                        
                        if (e2eResult.result != 'SUCCESS') {
                            error("E2E tests failed - not deploying to production")
                        }
                    }
                }
            }
            post {
                always {
                    sh 'docker rmi "frontend-e2e:${BUILD_NUMBER}" || true'
                }
            }
        }
        
        stage('Deploy to Production S3') {
            when { 
                anyOf {
                    branch 'main'
                    branch 'release/*'
                }
            }
            steps {
                retry(3) {
                    sh '''
                        aws s3 sync build/static/ s3://${S3_BUCKET}/static/ \
                            --cache-control "max-age=31536000,public,immutable" \
                            --delete
                        
                        aws s3 sync build/ s3://${S3_BUCKET}/ \
                            --cache-control "max-age=0,no-cache,no-store,must-revalidate" \
                            --exclude "static/*" \
                            --delete
                    '''
                }
            }
        }
        
        stage('CloudFront Invalidation') {
            when { 
                anyOf {
                    branch 'main'
                    branch 'release/*'
                }
            }
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    sh '''
                        INVALIDATION_ID=$(aws cloudfront create-invalidation \
                            --distribution-id ${CLOUDFRONT_DISTRIBUTION_ID} \
                            --paths "/*" \
                            --query 'Invalidation.Id' \
                            --output text)
                        
                        aws cloudfront wait invalidation-completed \
                            --distribution-id ${CLOUDFRONT_DISTRIBUTION_ID} \
                            --id $INVALIDATION_ID
                    '''
                }
            }
        }
        
        stage('Production Smoke Tests') {
            when { 
                anyOf {
                    branch 'main'
                    branch 'release/*'
                }
            }
            steps {
                timeout(time: 2, unit: 'MINUTES') {
                    sh '''
                        # Test CloudFront distribution
                        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://${CLOUDFRONT_DOMAIN}/")
                        if [ "$HTTP_STATUS" != "200" ]; then
                            echo "Frontend health check failed: $HTTP_STATUS"
                            exit 1
                        fi
                        
                        # Test key pages
                        curl -f "https://${CLOUDFRONT_DOMAIN}/" 
                        
                        echo "Frontend smoke tests passed"
                    '''
                }
            }
        }
    }
    
    post {
        always {
            script {
                def status = currentBuild.result ?: 'SUCCESS'
                emailext(
                    to: "${TEST_EMAIL}",
                    subject: "Frontend Build #${BUILD_NUMBER} - ${status}",
                    body: """
                        Pipeline: ${status}
                        Build: #${BUILD_NUMBER}
                        Duration: ${currentBuild.durationString}
                        
                        ${status == 'SUCCESS' ? 
                            "Live at: https://${CLOUDFRONT_DOMAIN}/" : 
                            "Build failed - check logs"}
                        
                        Details: ${BUILD_URL}
                    """
                )
            }
            
            sh '''
                rm -rf build || true
                docker system prune -f || true
            '''
            cleanWs()
        }
        success {
            echo 'Frontend deployment completed successfully!'
        }
        failure {
            echo 'Frontend deployment failed!'
        }
    }
}