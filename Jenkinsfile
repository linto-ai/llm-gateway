def notifyLintoDeploy(service_name, tag, commit_sha) {
    echo "Notifying linto-deploy for ${service_name}:${tag} (commit: ${commit_sha})..."
    withCredentials([usernamePassword(
        credentialsId: 'linto-deploy-bot',
        usernameVariable: 'GITHUB_APP',
        passwordVariable: 'GITHUB_TOKEN'
    )]) {
        writeFile file: 'payload.json', text: "{\"event_type\":\"update-service\",\"client_payload\":{\"service\":\"${service_name}\",\"tag\":\"${tag}\",\"commit_sha\":\"${commit_sha}\"}}"
        sh 'curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" -H "Accept: application/vnd.github.v3+json" -d @payload.json https://api.github.com/repos/linto-ai/linto-deploy/dispatches'
    }
}

// Best-effort deploy of a freshly built image to the staging cluster (full CI/CD).
// SSH host + key come from Jenkins credentials (nothing host-specific in the repo);
// no-op if those credentials are absent.
def stagingDeploy(image_name, tag) {
    try {
        withCredentials([
            sshUserPrivateKey(credentialsId: 'staging-deploy-ssh', keyFileVariable: 'SSH_KEY', usernameVariable: 'SSH_USER'),
            string(credentialsId: 'staging-deploy-host', variable: 'DEPLOY_HOST')
        ]) {
            sh "ssh -i \$SSH_KEY -o StrictHostKeyChecking=no \$SSH_USER@\$DEPLOY_HOST 'staging-deploy ${image_name} ${tag}'"
        }
    } catch (err) {
        echo "Staging auto-deploy skipped for ${image_name} (deploy credentials absent): ${err}"
    }
}

// Best-effort redeploy of preprod after a latest-unstable push (full CI/CD).
// SSH host + key come from Jenkins credentials (nothing host-specific in the repo);
// no-op if those credentials are absent.
def preprodDeploy(image_name) {
    try {
        withCredentials([
            sshUserPrivateKey(credentialsId: 'preprod-deploy-ssh', keyFileVariable: 'PP_SSH_KEY', usernameVariable: 'PP_SSH_USER'),
            string(credentialsId: 'preprod-deploy-host', variable: 'PP_DEPLOY_HOST')
        ]) {
            sh "ssh -i \$PP_SSH_KEY -o StrictHostKeyChecking=no \$PP_SSH_USER@\$PP_DEPLOY_HOST 'preprod-deploy ${image_name}'"
        }
    } catch (err) {
        echo "Preprod auto-deploy skipped for ${image_name} (deploy credentials absent): ${err}"
    }
}

pipeline {
    agent any
    environment {
        DOCKER_HUB_REPO_BACKEND = "lintoai/llm-gateway"
        DOCKER_HUB_REPO_FRONTEND = "lintoai/llm-gateway-frontend"
        DOCKER_HUB_CRED = 'docker-hub-credentials'
        STAGING_REGISTRY_BACKEND = "registry.staging.linto.ai/lintoai/llm-gateway"
        STAGING_REGISTRY_FRONTEND = "registry.staging.linto.ai/lintoai/llm-gateway-frontend"
        STAGING_REGISTRY_CRED = 'staging-registry-credentials'
        VERSION = ''
    }

    stages{
        stage('Docker build for master branch'){
            when{
                branch 'main'
            }
            steps {
                echo 'Publishing latest'
                script {
                    def commit_sha = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()

                    VERSION = sh(
                        returnStdout: true,
                        script: "awk -v RS='' '/#/ {print; exit}' RELEASE.md | head -1 | sed 's/#//' | sed 's/ //'"
                    ).trim()

                    // Build and push backend image
                    backendImage = docker.build("${env.DOCKER_HUB_REPO_BACKEND}", "-f Dockerfile .")
                    docker.withRegistry('https://registry.hub.docker.com', env.DOCKER_HUB_CRED) {
                        backendImage.push("${VERSION}")
                        backendImage.push('latest')
                    }
                    notifyLintoDeploy('llm-gateway', VERSION, commit_sha)

                    // Build and push frontend image
                    frontendImage = docker.build("${env.DOCKER_HUB_REPO_FRONTEND}", "-f frontend/Dockerfile frontend/")
                    docker.withRegistry('https://registry.hub.docker.com', env.DOCKER_HUB_CRED) {
                        frontendImage.push("${VERSION}")
                        frontendImage.push('latest')
                    }
                    notifyLintoDeploy('llm-gateway-frontend', VERSION, commit_sha)
                }
            }
        }

        stage('Docker build for next (unstable) branch'){
            when{
                branch 'next'
            }
            steps {
                echo 'Publishing unstable'
                script {
                    def changedFiles = sh(returnStdout: true, script: 'git diff --name-only HEAD^ HEAD').trim()
                    // Skip the latest-unstable rebuild for purely CI/docs commits
                    if (changedFiles.readLines().every { it == 'Jenkinsfile' || it.endsWith('.md') }) {
                        echo "Only CI/docs changed (${changedFiles}); skip latest-unstable rebuild"
                        return
                    }

                    VERSION = sh(
                        returnStdout: true,
                        script: "awk -v RS='' '/#/ {print; exit}' RELEASE.md | head -1 | sed 's/#//' | sed 's/ //'"
                    ).trim()

                    // Build and push backend image
                    backendImage = docker.build("${env.DOCKER_HUB_REPO_BACKEND}", "-f Dockerfile .")
                    docker.withRegistry('https://registry.hub.docker.com', env.DOCKER_HUB_CRED) {
                        backendImage.push('latest-unstable')
                    }
                    preprodDeploy('llm-gateway')

                    // Build and push frontend image
                    frontendImage = docker.build("${env.DOCKER_HUB_REPO_FRONTEND}", "-f frontend/Dockerfile frontend/")
                    docker.withRegistry('https://registry.hub.docker.com', env.DOCKER_HUB_CRED) {
                        frontendImage.push('latest-unstable')
                    }
                    preprodDeploy('llm-gateway-frontend')
                }
            }
        }

        stage('Docker build for staging branches'){
            when{
                branch 'staging/*'
            }
            steps {
                echo 'Building staging feature-branch images (private registry, never Docker Hub)'
                script {
                    def slug = env.BRANCH_NAME.replaceFirst('^staging/', '').replaceAll('[^a-zA-Z0-9]+', '-').toLowerCase()
                    def tag = "dev-${slug}"

                    def backendImage = docker.build("${env.STAGING_REGISTRY_BACKEND}", "-f Dockerfile .")
                    docker.withRegistry('https://registry.staging.linto.ai', env.STAGING_REGISTRY_CRED) {
                        backendImage.push(tag)
                    }
                    stagingDeploy('llm-gateway', tag)

                    def frontendImage = docker.build("${env.STAGING_REGISTRY_FRONTEND}", "-f frontend/Dockerfile frontend/")
                    docker.withRegistry('https://registry.staging.linto.ai', env.STAGING_REGISTRY_CRED) {
                        frontendImage.push(tag)
                    }
                    stagingDeploy('llm-gateway-frontend', tag)
                }
            }
        }
    }// end stages
}
