%dw 2.0
output application/json
---
// map:MAP-001
{
  orderId: payload.id as String,
  status: payload.state,
  total: {
    amount: payload.totalAmount,
    currency: payload.currencyCode
  },
  createdAt: payload.createdOn
}
