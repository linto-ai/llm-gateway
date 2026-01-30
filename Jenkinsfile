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

pipeline {
    agent any
    environment {
        DOCKER_HUB_REPO_BACKEND = "lintoai/llm-gateway"
        DOCKER_HUB_REPO_FRONTEND = "lintoai/llm-gateway-frontend"
        DOCKER_HUB_CRED = 'docker-hub-credentials'
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
                    def commit_sha = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()

                    VERSION = sh(
                        returnStdout: true,
                        script: "awk -v RS='' '/#/ {print; exit}' RELEASE.md | head -1 | sed 's/#//' | sed 's/ //'"
                    ).trim()

                    // Build and push backend image
                    backendImage = docker.build("${env.DOCKER_HUB_REPO_BACKEND}", "-f Dockerfile .")
                    docker.withRegistry('https://registry.hub.docker.com', env.DOCKER_HUB_CRED) {
                        backendImage.push('latest-unstable')
                    }

                    // Build and push frontend image
                    frontendImage = docker.build("${env.DOCKER_HUB_REPO_FRONTEND}", "-f frontend/Dockerfile frontend/")
                    docker.withRegistry('https://registry.hub.docker.com', env.DOCKER_HUB_CRED) {
                        frontendImage.push('latest-unstable')
                    }
                }
            }
        }
    }// end stages
}
