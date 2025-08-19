pipeline {
    agent any
    
    environment {
        APP_NAME = 'automarkly-frontend'
        BUILD_NUMBER = "${env.BUILD_NUMBER}"
        AWS_ACCOUNT_ID = credentials('aws-account-id')
        AWS_REGION = credentials('aws_region')
        ECR_REPO_FRONTEND = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/automarkly/emailservice-frontend"
        ECR_REPO_BACKEND = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/automarkly/emailservice-backend"
        GITOPS_REPO = 'git@github.com:sara-golombeck/gitops-automarkly.git'
        HELM_VALUES_PATH = 'charts/automarkly/values.yaml'
    }
    triggers {
        githubPush()
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Unit Tests') {
            steps {
                sh '''
                    docker build -f Dockerfile.test -t "${APP_NAME}:test-${BUILD_NUMBER}" .
                    mkdir -p coverage
                    docker run --rm \
                        -v "${PWD}/coverage:/app/coverage" \
                        "${APP_NAME}:test-${BUILD_NUMBER}"
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'coverage/**/*', allowEmptyArchive: true
                }
            }
        }
        
        stage('Build Application') {
            steps {
                script {
                    docker.build("${APP_NAME}:${BUILD_NUMBER}")
                }
            }
        }
        
        stage('E2E Tests') {
            steps {
                withCredentials([string(credentialsId: 'ECR_TAG_BACK', variable: 'ECR_TAG_BACK')]) {
                    sh '''
                        cat > .env <<EOF
                        POSTGRES_DB=automarkly_test
                        POSTGRES_USER=postgres
                        POSTGRES_PASSWORD=postgres123
                        COMPOSE_PROJECT_NAME=automarkly_e2e
                        ECR_TAG_BACK=${ECR_TAG_BACK}
                        EOF
                        
                        docker compose -f docker-compose.e2e.yml up -d
                        
                        docker build -f tests/integration/Dockerfile -t "${APP_NAME}:e2e-${BUILD_NUMBER}" tests/integration/
                        sleep 15
                        docker run --rm \
                            --network automarkly_e2e_app-network \
                            -e BASE_URL=http://emailservice-frontend:80 \
                            "${APP_NAME}:e2e-${BUILD_NUMBER}"
                    '''
                }
            }
            post {
                always {
                    sh '''
                        docker compose -f docker-compose.e2e.yml logs > e2e-logs.txt || true
                        docker compose -f docker-compose.e2e.yml down -v || true
                    '''
                    archiveArtifacts artifacts: 'e2e-logs.txt', allowEmptyArchive: true
                }
            }
        }
        
        stage('Create Version Tag') {
            when { 
                branch 'main' 
            }
            steps {
                script {
                    echo "Creating version tag..."
                    
                    sshagent(credentials: ['github']) {
                        sh "git fetch --tags"
                        
                        def newTag = "1.0.0"  // default
                        
                        try {
                            def lastTag = sh(script: "git tag --sort=-version:refname | head -1", returnStdout: true).trim()
                            if (lastTag && lastTag != '') {
                                echo "Found existing tag: ${lastTag}"
                                
                                def v = lastTag.tokenize('.')
                                if (v.size() >= 3) {
                                    def newPatch = v[2].toInteger() + 1
                                    newTag = v[0] + "." + v[1] + "." + newPatch
                                }
                            } else {
                                echo "No existing tags found, starting from 1.0.0"
                            }
                        } catch (Exception e) {
                            echo "Error reading tags: ${e.getMessage()}, starting from 1.0.0"
                        }
                        
                        echo "Generated new tag: ${newTag}"
                        env.MAIN_TAG = newTag
                        echo "Version tag ${env.MAIN_TAG} prepared successfully"
                    }
                }
            }
        }
        
        stage('Push to ECR') {
            when { 
                branch 'main'
            }
            steps {
                script {
                    if (!env.MAIN_TAG || env.MAIN_TAG == '' || env.MAIN_TAG == 'null') {
                        error("env.MAIN_TAG is empty, null, or invalid: '${env.MAIN_TAG}'")
                    }
                    
                    echo "Pushing ${env.MAIN_TAG} to ECR..."
                    
                    sh '''
                        aws ecr get-login-password --region "${AWS_REGION}" | \
                            docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                        
                        docker tag "${APP_NAME}:${BUILD_NUMBER}" "${ECR_REPO_FRONTEND}:${MAIN_TAG}"
                        docker tag "${APP_NAME}:${BUILD_NUMBER}" "${ECR_REPO_FRONTEND}:latest"
                        
                        docker push "${ECR_REPO_FRONTEND}:${MAIN_TAG}"
                        docker push "${ECR_REPO_FRONTEND}:latest"
                    '''
                    
                    echo "Successfully pushed ${env.MAIN_TAG} to ECR"
                }
            }
        }
        
        stage('Deploy via GitOps') {
            when { 
                branch 'main' 
            }
            steps {
                script {
                    if (!env.MAIN_TAG || env.MAIN_TAG == '') {
                        echo "WARNING: env.MAIN_TAG not set, skipping GitOps update"
                        return
                    }
                    
                    sshagent(['github']) {
                        sh '''
                            rm -rf gitops-config
                            echo "Cloning GitOps repository..."
                            git clone "${GITOPS_REPO}" gitops-config
                        '''
                        
                        withCredentials([
                            string(credentialsId: 'git-username', variable: 'GIT_USERNAME'),
                            string(credentialsId: 'git-email', variable: 'GIT_EMAIL')
                        ]) {
                            dir('gitops-config') {
                                sh '''
                                    git config user.email "${GIT_EMAIL}"
                                    git config user.name "${GIT_USERNAME}"

                                    sed -i "s|frontendTag: \\".*\\"|frontendTag: \\"${MAIN_TAG}\\"|g" "${HELM_VALUES_PATH}"
                                    
                                    if git diff --quiet "${HELM_VALUES_PATH}"; then
                                        echo "No changes to deploy - version ${MAIN_TAG} already deployed"
                                    else
                                        git add "${HELM_VALUES_PATH}"
                                        git commit -m "Deploy frontend v${MAIN_TAG} - Build ${BUILD_NUMBER}"
                                        git push origin main
                                        echo "GitOps updated: ${MAIN_TAG}"
                                    fi
                                '''
                            }
                        }
                    }
                }
            }
        }
        
        stage('Push Git Tag') {
            when { 
                branch 'main'
            }
            steps {
                script {
                    if (!env.MAIN_TAG || env.MAIN_TAG == '') {
                        echo "WARNING: env.MAIN_TAG not set, skipping git tag"
                        return
                    }
                    
                    echo "Pushing tag ${env.MAIN_TAG} to repository..."
                    
                    sshagent(credentials: ['github']) {
                        withCredentials([
                            string(credentialsId: 'git-username', variable: 'GIT_USERNAME'),
                            string(credentialsId: 'git-email', variable: 'GIT_EMAIL')
                        ]) {
                            sh '''
                                git config user.email "${GIT_EMAIL}"
                                git config user.name "${GIT_USERNAME}"
                                
                                git tag -a "${MAIN_TAG}" -m "Release ${MAIN_TAG} - Build ${BUILD_NUMBER}"
                                git push origin "${MAIN_TAG}"
                            '''
                        }
                    }
                    
                    echo "Tag ${env.MAIN_TAG} pushed successfully"
                }
            }
        }
    }
    
    post {
        always {
            sh '''
                docker compose -f docker-compose.e2e.yml down -v || true
                rm -rf gitops-config || true
                docker rmi "${APP_NAME}:test-${BUILD_NUMBER}" || true
                docker rmi "${APP_NAME}:e2e-${BUILD_NUMBER}" || true
                docker image prune -f || true
                rm -f .env
            '''
            cleanWs()
        }
        success {
            echo 'Frontend pipeline completed successfully!'
        }
        failure {
            echo 'Frontend pipeline failed!'
        }
    }
}