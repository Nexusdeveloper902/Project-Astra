use serde::{Deserialize, Serialize};
use serde_json::Value;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub id: String,
    pub method: String,
    pub params: Value,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub id: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<JsonRpcError>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
}

impl JsonRpcResponse {
    pub fn success(id: String, result: Value) -> Self {
        JsonRpcResponse {
            jsonrpc: "2.0".to_string(),
            id,
            result: Some(result),
            error: None,
        }
    }

    pub fn error(id: String, code: i32, message: &str) -> Self {
        JsonRpcResponse {
            jsonrpc: "2.0".to_string(),
            id,
            result: None,
            error: Some(JsonRpcError {
                code,
                message: message.to_string(),
            }),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn success_response_has_result_and_no_error() {
        let response = JsonRpcResponse::success("req-1".to_string(), json!({"status": "queued"}));

        assert_eq!(response.jsonrpc, "2.0");
        assert_eq!(response.id, "req-1");
        assert_eq!(response.result, Some(json!({"status": "queued"})));
        assert!(response.error.is_none());
    }

    #[test]
    fn error_response_has_error_and_no_result() {
        let response = JsonRpcResponse::error("req-1".to_string(), -32001, "suspended");

        assert_eq!(response.jsonrpc, "2.0");
        assert_eq!(response.id, "req-1");
        assert!(response.result.is_none());
        assert_eq!(response.error.as_ref().unwrap().code, -32001);
        assert_eq!(response.error.as_ref().unwrap().message, "suspended");
    }

    #[test]
    fn success_response_serializes_without_error_field() {
        let serialized = serde_json::to_value(JsonRpcResponse::success(
            "req-1".to_string(),
            json!({"ok": true}),
        ))
        .unwrap();

        assert_eq!(serialized["jsonrpc"], "2.0");
        assert_eq!(serialized["result"], json!({"ok": true}));
        assert!(serialized.get("error").is_none());
    }

    #[test]
    fn error_response_serializes_without_result_field() {
        let serialized = serde_json::to_value(JsonRpcResponse::error(
            "req-1".to_string(),
            -1,
            "bad request",
        ))
        .unwrap();

        assert_eq!(serialized["error"], json!({"code": -1, "message": "bad request"}));
        assert!(serialized.get("result").is_none());
    }

    #[test]
    fn request_deserializes_params_as_json_value() {
        let request: JsonRpcRequest = serde_json::from_value(json!({
            "jsonrpc": "2.0",
            "id": "req-1",
            "method": "ui.input",
            "params": {"text": "hello"}
        }))
        .unwrap();

        assert_eq!(request.method, "ui.input");
        assert_eq!(request.params["text"], "hello");
    }
}
