@Library('GitHub') _

def buildPodYml = libraryResource 'buildPodMaven25.yml'

pipeline {
  agent {
    kubernetes {
      yaml buildPodYml
    }
  }

  options {
    // PaddleOCR model download makes the first docker build slow (~15–20 min).
    timeout(time: 45, unit: 'MINUTES')
    // Prevent concurrent deploys racing on the same k8s deployment.
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  stages {
    stage('Build') {
      steps {
        // Build and push Docker image
        dockerBuild("${registry}/${project}:${branch}")
      }
    }

    stage('Deploy') {
      container('kubectl') {
        script {
          def namespace = "${project}-${branch}" as String
          status = sh(
            returnStatus: true,
            script: "kubectl get namespace $namespace"
          )

          if (status == 0) {
            println "$namespace namespace exists"
          } else {
            sh "kubectl create namespace $namespace"
          }

          sh "kubectl -n $namespace apply -f k8s/"
        }
      }
    }
  }
}
