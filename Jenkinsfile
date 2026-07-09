pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build & Test') {
            steps {
                sh '''
                    for service in users-service books-service loans-service; do
                        echo "Testing $service"
                        cd $service
                        python3 -m venv .venv
                        . .venv/bin/activate
                        pip install -r requirements.txt
                        pytest tests/ -v
                        deactivate
                        cd ..
                    done
                '''
            }
        }

        stage('Build Docker Images') {
            steps {
                sh 'docker compose build'
            }
        }

        stage('Deploy') {
            steps {
                // cd into PROJECT_DIR (bind-mounted into the jenkins
                // container at this same absolute path, see
                // docker-compose.jenkins.yml) rather than this build's own
                // checkout workspace. Jenkins drives the HOST's Docker
                // daemon via a mounted socket, and that daemon resolves
                // docker-compose.yml's relative bind mounts (e.g.
                // ./gateway/nginx.conf) against real host paths - which the
                // default Jenkins workspace (inside the jenkins_home named
                // volume) is not. A plain `cd` inside one sh step (rather
                // than Pipeline's dir() step) avoids Jenkins trying to
                // create its own tracking directory next to an external
                // path it doesn't own.
                sh '''
                    cd "$PROJECT_DIR"
                    docker compose down
                    docker compose up -d
                '''
            }
        }
    }
}
