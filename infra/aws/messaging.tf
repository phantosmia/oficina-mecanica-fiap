# Mensageria do orquestrador da saga (RFC-0007, contrato em docs/saga.md).
#
# O OS Service não publica eventos: ele envia comandos para a fila de cada
# participante e recebe as respostas numa fila só, os-saga-eventos, que assina
# os tópicos de eventos dos 4 participantes. Filas de comando e tópicos são
# criados pelo Terraform de cada participante, que por isso precisa ser
# aplicado antes deste (ordem em docs/arquitetura.md).

locals {
  messaging_prefix  = "oficina-${var.environment}"
  saga_participants = toset(["estoque", "orcamento", "pagamento", "execucao"])
}

data "aws_sns_topic" "participant_events" {
  for_each = local.saga_participants

  name = "${local.messaging_prefix}-${each.key}-eventos"
}

data "aws_sqs_queue" "participant_commands" {
  for_each = local.saga_participants

  name = "${local.messaging_prefix}-${each.key}-comandos"
}

resource "aws_sqs_queue" "saga_events_dlq" {
  name                      = "${local.messaging_prefix}-os-saga-eventos-dlq"
  message_retention_seconds = 1209600

  tags = local.common_tags
}

resource "aws_sqs_queue" "saga_events" {
  name = "${local.messaging_prefix}-os-saga-eventos"

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.saga_events_dlq.arn
    maxReceiveCount     = 5
  })

  tags = local.common_tags
}

data "aws_iam_policy_document" "saga_events" {
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.saga_events.arn]

    principals {
      type        = "Service"
      identifiers = ["sns.amazonaws.com"]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [for topic in data.aws_sns_topic.participant_events : topic.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "saga_events" {
  queue_url = aws_sqs_queue.saga_events.id
  policy    = data.aws_iam_policy_document.saga_events.json
}

# Entrega crua (sem o envelope do SNS), como no docker-compose.
resource "aws_sns_topic_subscription" "saga_events" {
  for_each = local.saga_participants

  topic_arn            = data.aws_sns_topic.participant_events[each.key].arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.saga_events.arn
  raw_message_delivery = true

  depends_on = [aws_sqs_queue_policy.saga_events]
}
