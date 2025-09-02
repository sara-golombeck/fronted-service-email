pipeline {
    agent any
    
    environment {
        APP_NAME = 'automarkly-frontend'
        BUILD_NUMBER = "${env.BUILD_NUMBER}"
        AWS_REGION = 'ap-south-1'
        TEST_EMAIL = 'sara.beck.dev@gmail.com'
        
        // S3 and CloudFront - from Jenkins Credentials
        S3_BUCKET = credentials('s3-static-bucket')
        CLOUDFRONT_DISTRIBUTION_ID = credentials('cloudfront-distribution-id')
        CLOUDFRONT_DOMAIN = credentials('cloudfront-domain')
        
        GITOPS_REPO = credentials('gitops-repo-url')
        HELM_VALUES_PATH = 'charts/email-service/values.yaml'
        PRODUCTION_URL = credentials('production-url')
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
                    # Run tests in Docker container
                    docker build -f Dockerfile.test -t "${APP_NAME}:test-${BUILD_NUMBER}" .
                    
                    # Run tests and extract results
                    mkdir -p test-results coverage
                    docker run --rm \
                        -v "${PWD}/test-results:/app/test-results" \
                        -v "${PWD}/coverage:/app/coverage" \
                        "${APP_NAME}:test-${BUILD_NUMBER}"
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'test-results/**/*,coverage/**/*', allowEmptyArchive: true
                    sh 'docker rmi "${APP_NAME}:test-${BUILD_NUMBER}" || true'
                }
            }
        }
        
        stage('Build Static Files') {
            when {
                anyOf {
                    branch 'main'
                    branch 'feature/*'
                    branch 'release/*'
                }
            }
            steps {
                sh '''
                    # Build static files using Docker
                    docker build --target s3-build -t "${APP_NAME}:build-${BUILD_NUMBER}" .
                    
                    # Extract build files from container
                    mkdir -p build
                    docker run --rm -v "${PWD}/build:/output" "${APP_NAME}:build-${BUILD_NUMBER}" \
                        sh -c "cp -r /app/build/* /output/ 2>/dev/null || echo 'No build files found'"
                    
                    # Verify build output exists
                    if [ ! -d "build/static" ]; then
                        echo "❌ Build failed - no static files generated"
                        exit 1
                    fi
                    
                    ls -la build/
                    echo "✅ Docker build completed successfully"
                '''
            }
            post {
                always {
                    sh 'docker rmi "${APP_NAME}:build-${BUILD_NUMBER}" || true'
                }
            }
        }
        
        stage('Upload to S3 - Staging') {
            when {
                anyOf {
                    branch 'main'
                    branch 'feature/*'
                    branch 'release/*'
                }
            }
            // Ensure build completed successfully
            when {
                expression { fileExists('build/static') }
            }
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    sh '''
                        # Upload static assets with long cache
                        aws s3 sync build/static/ s3://${S3_BUCKET}/staging/${BUILD_NUMBER}/static/ \\
                            --cache-control "max-age=31536000,public,immutable" \\
                            --delete
                        
                        # Upload HTML and service worker with no cache
                        aws s3 sync build/ s3://${S3_BUCKET}/staging/${BUILD_NUMBER}/ \\
                            --cache-control "max-age=0,no-cache,no-store,must-revalidate" \\
                            --exclude "static/*" \\
                            --delete
                        
                        echo "✅ Staging files uploaded to: s3://${S3_BUCKET}/staging/${BUILD_NUMBER}/"
                    '''
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
                build job: 'e2e-email-service',
                      parameters: [
                          string(name: 'STATIC_FILES_URL', value: "https://${CLOUDFRONT_DOMAIN}/staging/${BUILD_NUMBER}"),
                          string(name: 'TEST_EMAIL', value: "${TEST_EMAIL}")
                      ],
                      wait: true
            }
        }
        
        stage('Create Version Tag') {
            when { 
                anyOf {
                    branch 'main'
                    branch 'release/*'
                }
            }
            steps {
                script {
                    sh '''
                        # Generate semantic version
                        COMMIT_COUNT=$(git rev-list --count HEAD)
                        SHORT_SHA=$(git rev-parse --short HEAD)
                        VERSION="1.0.${COMMIT_COUNT}-${SHORT_SHA}"
                        echo $VERSION > version.txt
                    '''
                    env.MAIN_TAG = readFile('version.txt').trim()
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
                        echo "🚀 Deploying to production S3..."
                        
                        # Upload static assets with long cache
                        aws s3 sync build/static/ s3://${S3_BUCKET}/static/ \\
                            --cache-control "max-age=31536000,public,immutable" \\
                            --delete
                        
                        # Upload HTML and service worker with no cache
                        aws s3 sync build/ s3://${S3_BUCKET}/ \\
                            --cache-control "max-age=0,no-cache,no-store,must-revalidate" \\
                            --exclude "static/*" \\
                            --delete
                        
                        echo "✅ Production files uploaded to: s3://${S3_BUCKET}/"
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
                        echo "🔄 Creating CloudFront invalidation..."
                        
                        INVALIDATION_ID=$(aws cloudfront create-invalidation \\
                            --distribution-id ${CLOUDFRONT_DISTRIBUTION_ID} \\
                            --paths "/*" \\
                            --query 'Invalidation.Id' \\
                            --output text)
                        
                        echo "Invalidation ID: $INVALIDATION_ID"
                        
                        # Wait for invalidation to complete
                        aws cloudfront wait invalidation-completed \\
                            --distribution-id ${CLOUDFRONT_DISTRIBUTION_ID} \\
                            --id $INVALIDATION_ID
                        
                        echo "✅ CloudFront invalidation completed!"
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
                timeout(time: 3, unit: 'MINUTES') {
                    sh '''
                        echo "🧪 Running production smoke tests..."
                        
                        # Test CloudFront distribution
                        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://${CLOUDFRONT_DOMAIN}/")
                        if [ "$HTTP_STATUS" != "200" ]; then
                            echo "❌ CloudFront health check failed: $HTTP_STATUS"
                            exit 1
                        fi
                        
                        # Test static assets
                        curl -f "https://${CLOUDFRONT_DOMAIN}/static/css/" || echo "CSS files check"
                        curl -f "https://${CLOUDFRONT_DOMAIN}/static/js/" || echo "JS files check"
                        
                        echo "✅ Production smoke tests passed!"
                    '''
                }
            }
        }
    }
    
    post {
        always {
            script {
                def status = currentBuild.result ?: 'SUCCESS'
                def emoji = status == 'SUCCESS' ? '✅' : '❌'
                
                emailext(
                    to: "${TEST_EMAIL}",
                    subject: "${emoji} ${APP_NAME} Build #${BUILD_NUMBER} - ${status}",
                    body: """
                        Pipeline: ${status}
                        Build: #${BUILD_NUMBER}
                        Duration: ${currentBuild.durationString}
                        
                        ${status == 'SUCCESS' ? 
                            "🌐 Live at: https://${CLOUDFRONT_DOMAIN}/" : 
                            "❌ Build failed - check logs"}
                        
                        📊 Details: ${BUILD_URL}
                    """
                )
            }
            
            sh '''
                # Cleanup
                rm -rf node_modules build version.txt || true
            '''
            cleanWs()
        }
        success {
            echo '✅ Frontend S3 deployment completed successfully!'
        }
        failure {
            echo '❌ Frontend S3 deployment failed!'
        }
    }
}