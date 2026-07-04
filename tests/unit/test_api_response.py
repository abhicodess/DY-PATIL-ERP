from utils.api_response import success_response, error_response, paginated_response, get_request_id

def test_get_request_id():
    req_id = get_request_id()
    assert req_id is not None
    assert len(req_id) == 36

def test_api_responses(app):
    with app.app_context():
        # success response
        resp, status = success_response({"foo": "bar"}, "Success message")
        assert status == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["message"] == "Success message"
        assert data["data"]["foo"] == "bar"

        # error response
        resp_err, status_err = error_response("Error message", "INVALID_ARG", 400)
        assert status_err == 400
        data_err = resp_err.get_json()
        assert data_err["success"] is False
        assert data_err["error"]["code"] == "INVALID_ARG"

        # paginated response
        resp_pag, status_pag = paginated_response([{"id": 1}], 10, 1, 2)
        assert status_pag == 200
        data_pag = resp_pag.get_json()
        pagination = data_pag["meta"]["pagination"]
        assert pagination["total"] == 10
        assert pagination["page"] == 1
        assert pagination["per_page"] == 2
        assert pagination["total_pages"] == 5
        assert pagination["has_next"] is True
        assert pagination["has_prev"] is False
