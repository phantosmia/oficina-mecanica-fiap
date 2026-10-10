# language: pt
Funcionalidade: Fluxo de uma ordem de serviço pelos microsserviços (Saga orquestrada)
  Como oficina mecânica
  Quero que a abertura, o diagnóstico, o orçamento, o pagamento e o reparo de uma OS
  sejam coordenados entre os microsserviços, com compensação em caso de falha
  Para que nenhuma OS termine com peças presas, orçamento aberto ou cobrança indevida

  Contexto:
    Dado que o administrador abriu uma OS para o veículo "BRA2E19" com o problema "Luz do óleo acendendo"

  Cenário: Fluxo completo, da abertura à entrega
    Então o comando "EnfileirarDiagnostico" é enviado para "execucao"
    Quando a Execução confirma que a OS entrou na fila de diagnóstico
    E o mecânico inicia o diagnóstico
    Então a OS fica com status "em_diagnostico"
    Quando o mecânico conclui o diagnóstico com 1 "Troca de óleo" a 150.00 e 4 "Óleo 5W30" a 45.00
    Então o comando "ReservarPecas" é enviado para "estoque"
    E a OS tem total de 330.00
    Quando o Estoque reserva as peças
    Então o comando "GerarOrcamento" é enviado para "orcamento"
    Quando o Orçamento é gerado e enviado ao cliente
    Então a OS fica com status "aguardando_aprovacao"
    Quando o cliente aprova o orçamento
    Então o comando "CriarCobranca" é enviado para "pagamento"
    E a OS fica com status "aguardando_pagamento"
    Quando o Pagamento cria a cobrança no Mercado Pago
    E o pagamento é confirmado
    Então o comando "ConfirmarBaixa" é enviado para "estoque"
    Quando o Estoque confirma a baixa das peças
    Então o comando "EnfileirarReparo" é enviado para "execucao"
    Quando a Execução confirma que a OS entrou na fila de reparo
    Então a OS fica com status "em_execucao"
    Quando o mecânico inicia e conclui o reparo
    Então a OS fica com status "finalizada"
    E a saga fica no estado "CONCLUIDA"
    Quando o administrador entrega o veículo
    Então a OS fica com status "entregue"
    E o histórico da OS é "recebida, em_diagnostico, aguardando_aprovacao, aguardando_pagamento, em_execucao, finalizada, entregue"

  Cenário: Cliente recusa o orçamento e as peças reservadas são liberadas
    Dado que a OS chegou até o orçamento aguardando aprovação
    Quando o cliente recusa o orçamento
    Então as compensações são enviadas uma de cada vez, na ordem "LiberarPecas"
    E a OS fica com status "recusada"
    E a saga fica no estado "CANCELADA"

  Cenário: Pagamento não concluído desfaz cobrança, orçamento e reserva
    Dado que a OS chegou até a cobrança criada
    Quando o pagamento é recusado pelo provedor
    Então as compensações são enviadas uma de cada vez, na ordem "CancelarCobranca, CancelarOrcamento, LiberarPecas"
    E a OS fica com status "cancelada"

  Cenário: Falha depois do pagamento estorna o cliente e devolve as peças
    Dado que a OS chegou até a baixa das peças confirmada
    Quando a Execução não aceita a OS na fila de reparo
    Então as compensações são enviadas uma de cada vez, na ordem "EstornarPagamento, CancelarOrcamento, DevolverPecas"
    E a OS fica com status "cancelada"
