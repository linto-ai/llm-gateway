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

                    // Build and push frontend image
                    frontendImage = docker.build("${env.DOCKER_HUB_REPO_FRONTEND}", "-f frontend/Dockerfile frontend/")
                    docker.withRegistry('https://registry.hub.docker.com', env.DOCKER_HUB_CRED) {
                        frontendImage.push("${VERSION}")
                        frontendImage.push('latest')
                    }
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
