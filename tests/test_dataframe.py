import wrangles
import os

def test_query():
    """
    Test using the ask function to query a dataframe
    """
    df = wrangles.DataFrame(
        wrangles.connectors.test.read(
            100,
            values={
                'id': '<code>',
                'brand': '<word>',
                'description': '<sentence>',
                'in_stock': '<boolean>',
                'price': '<number(0.01-100.00)>',
                'category': '<random(["Electronics", "Clothing", "Home", "Sports", "Toys"])>'
            }
        )
    )

    prices = df.wrangles.query("Get all rows where the price is greater than 50", api_key=os.environ['OPENAI_API_KEY'])['price']
    assert min(prices) > 50
