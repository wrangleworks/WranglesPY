import wrangles


def test_read():
    df = wrangles.recipe.run(
        """
        read:
          - http:
              url: https://marvin.wrangle.works
        """
    )
    assert isinstance(df["message"][0], str)


def test_run():
    from wrangles.connectors import http

    test = http.run("https://marvin.wrangle.works")
    assert test == None


def test_read_oauth():
    """
    Test reading data using OAuth
    """
    df = wrangles.recipe.run(
        """
        read:
          - http:
              url: https://api.wrangle.works/model/content
              params:
                model_id: fc7d46e3-057f-47bd
              method: GET
              oauth:
                url: https://sso.wrangle.works/auth/realms/wrwx/protocol/openid-connect/token
                method: POST
                data: grant_type=password&username=${WRANGLES_USER}&password=${WRANGLES_PASSWORD}&client_id=services
                headers:
                  Content-Type: application/x-www-form-urlencoded
        """
    )
    assert df.columns.tolist() == ["Settings", "Columns", "Data"]


def test_read_orient_tight():
    """
    Test reading data using OAuth
    """
    df = wrangles.recipe.run(
        """
        read:
          - http:
              url: https://api.wrangle.works/model/content
              params:
                model_id: fc7d46e3-057f-47bd
              method: GET
              orient: tight
              oauth:
                url: https://sso.wrangle.works/auth/realms/wrwx/protocol/openid-connect/token
                method: POST
                data: grant_type=password&username=${WRANGLES_USER}&password=${WRANGLES_PASSWORD}&client_id=services
                headers:
                  Content-Type: application/x-www-form-urlencoded
        """
    )
    assert df.columns.tolist() == ["Find", "Replace", "Notes"]
