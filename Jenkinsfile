@Library('GitHub') _

def buildPodYml = libraryResource 'buildPodMaven25.yml'

project = ""
branch = ""

pipeline {

  options {
    // Discard everything except the last 10 builds
    buildDiscarder(logRotator(numToKeepStr: '10'))
    // Don't build the same branch concurrently
    disableConcurrentBuilds()

    // Cleanup orphaned branch Kubernetes namespace
    branchTearDownExecutor 'Cleanup'
  }

  agent {
    kubernetes {
      yaml buildPodYml
    }
  }

  environment {
    branch = env.BRANCH_NAME.toLowerCase()
    project = getProject()
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

        script {
          branch = env.BRANCH_NAME.toLowerCase()
          registry = "registry.container-registry:5000"
          project = getProject()
          println "Project/Branch = " + project + "/" + branch
        }

        // Build and push Docker image
        dockerBuild("${registry}/${project}:${branch}")
      }
    }

    stage('Deploy') {
      steps {                                    // steps{} wrapper required for container()
        container('kubectl') {
          script {
            def namespace = "${project}-${branch}" as String
            def status = sh(                     // def keeps status local to this script block
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
}
