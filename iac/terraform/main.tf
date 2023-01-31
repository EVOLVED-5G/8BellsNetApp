resource "kubernetes_pod" "8BellsNetApp" {
  metadata {
    name = "8BellsNetApp"
    namespace = "evolved5g"
    labels = {
      app = "Add the NetApp app"
    }
  }

  spec {
    container {
      image = "dockerhub.hi.inet/evolved-5g/dummy-netapp:latest"
      name  = "dummy-netapp"
    }
  }
}

resource "kubernetes_service" "8BellsNetApp_service" {
  metadata {
    name = "Add the NetApp Service"
    namespace = "evolved5g"
  }
  spec {
    selector = {
      app = kubernetes_pod.8BellsNetApp.metadata.0.labels.app
    }
    port {
      port = 5000
      target_port = 5000
    }
  }
}
