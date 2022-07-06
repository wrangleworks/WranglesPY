import wrangles


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
    
  