import wrangles
from datetime import datetime


def test_data_generation1():
    recipe = """
    read:
        - test:
            rows: 5
            values:
                fixed value: example string
                code: <code(10)>
                boolean: <boolean>
                number: <number(2.718-3.141)>
                int: <int(0-100)>
                char: <char>
                word: <word>
                sentence: <sentence>
                list:
                    - apple
                    - strawberry
                    - pear
                    - banana
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['fixed value', 'code', 'boolean', 'number', 'int', 'char', 'word', 'sentence', 'list']
    
# Not valid int values
def test_data_generation_2():
    recipe = """
    read:
        - test:
            rows: 5
            values:
                int: <int>
                char: <char>
                word: <word>
                sentence: <NotFound>
                number: <number(2-13.13)>
                code: <code>
                dict: 
                    hello: good bye
                list:
                    - apple
                    - strawberry
                    - pear
                    - banana
    """
    df = wrangles.recipe.run(recipe)
    assert df.columns.tolist() == ['int', 'char', 'word', 'sentence', 'number', 'code', 'dict', 'list']
    
# testing todays date
def test_date_today_generation_3():
    recipe = """
    read:
      - test:
          rows: 1
          values:
            date: <date_today>
    """
    df = wrangles.recipe.run(recipe)
    assert df.iloc[0]['date'].date() == datetime.today().date()
    
# testing date ranges
def test_date_ranges_4():
    recipe = """
    read:
      - test:
          rows: 2
          values:
            date_range: <12-25-2022 to 12-31-2022>
    """
    df = wrangles.recipe.run(recipe)
    assert 1 # this will generate a random date. Testing that it works
  
def test_date_5():
    recipe = """
    read:
      - test:
          rows: 2
          values:
            dates: <date 12-25-2022>
    """
    df = wrangles.recipe.run(recipe)
    assert df.iloc[0]['dates'].strftime("%Y") == '2022'
    
def test_order_list():
    """
    Test using an order lists of values
    """
    recipe = """
    read:
      - test:
          rows: 3
          values:
            order_list:
              - apple
              - orange
              - banana
    """
    df = wrangles.recipe.run(recipe)
    assert df.iloc[0].tolist() == [['apple', 'orange', 'banana']]
    
def test_random_list():
    """
    Test using a random list (random<["true", "False"]>)
    """
    recipe = """
    read:
      - test:
          rows: 3
          values:
            random_list: random<["true", "false"]>
    """
    df = wrangles.recipe.run(recipe)
    assert df.iloc[0][0] == 'true' or df.iloc[0][0] == 'false'