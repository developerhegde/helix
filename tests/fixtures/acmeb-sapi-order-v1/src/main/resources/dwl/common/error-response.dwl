%dw 2.0
output application/json
---
{
  error: {
    code: vars.errorCode,
    message: "The request could not be completed",
    correlationId: correlationId,
    timestamp: now() as String {format: "yyyy-MM-dd'T'HH:mm:ss'Z'"}
  }
}
