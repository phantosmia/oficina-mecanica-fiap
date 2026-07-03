output "state_bucket_name" {
  description = "Bucket S3 usado pelo backend remoto."
  value       = aws_s3_bucket.terraform_state.bucket
}

output "lock_table_name" {
  description = "Tabela DynamoDB usada para lock do state."
  value       = aws_dynamodb_table.terraform_locks.name
}

output "backend_config" {
  description = "Configuração sugerida para terraform/aws/backend.hcl."
  value       = <<EOT
bucket         = "${aws_s3_bucket.terraform_state.bucket}"
key            = "aws/dev/terraform.tfstate"
region         = "${var.aws_region}"
dynamodb_table = "${aws_dynamodb_table.terraform_locks.name}"
encrypt        = true
EOT
}
