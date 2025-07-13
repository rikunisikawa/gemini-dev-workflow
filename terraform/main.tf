terraform {
  backend "s3" {
    bucket         = "gemini-dev-workslow-data-platform"
    key            = "terraform.tfstate"
    region         = "ap-northeast-1"
    dynamodb_table = "terraform-lock"
    encrypt        = true
  }
}
