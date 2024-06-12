import random
import string
import wrangles
import pytest


def test_write_and_read():
    """
    Write a random string to CKAN server,
    then read results back to verify
    """
    random_string = ''.join(random.choices(string.ascii_lowercase, k=8))
    recipe = """
    read:
      - test:
          rows: 5
          values:
            header: ${RANDOM_VALUE}
    
    write:
      - ckan:
          host: https://catalog.wrangle.works
          dataset: test
          file: test-${RANDOM_VALUE}.csv
          api_key: ${CKAN_API_KEY}
    """
    wrangles.recipe.run(
        recipe,
        variables={
            'RANDOM_VALUE': random_string
        }
    )

    df = wrangles.recipe.run(
        """
        read:
          - ckan:
              host: https://catalog.wrangle.works
              dataset: test
              file: test-${RANDOM_VALUE}.csv
              api_key: ${CKAN_API_KEY}
        """,
        variables={
            'RANDOM_VALUE': random_string
        }
    )
    assert df['header'].values[0] == random_string

def test_missing_apikey():
    """
    Check error if user omits API KEY
    """
    with pytest.raises(RuntimeError, match="Access Denied"):
        wrangles.recipe.run(
            """
            read:
            - ckan:
                host: https://catalog.wrangle.works
                dataset: test
                file: test.csv
            """
        )

def test_invalid_apikey():
    """
    Check error if user has invalid API KEY
    """
    with pytest.raises(RuntimeError, match="Access Denied"):
        wrangles.recipe.run(
            """
            read:
            - ckan:
                host: https://catalog.wrangle.works
                dataset: test
                file: test.csv
                api_key: aaaaaa
            """
        )

def test_missing_dataset():
    """
    Check error if dataset isn't found
    """
    with pytest.raises(ValueError, match="Unable to find dataset"):
        wrangles.recipe.run(
            """
            read:
            - ckan:
                host: https://catalog.wrangle.works
                dataset: aaaaaaaaaaaaa
                file: test.csv
                api_key: ${CKAN_API_KEY}
            """
        )


def test_missing_file():
    """
    Check error if file isn't found in the dataset
    """
    with pytest.raises(ValueError, match="File not found"):
        wrangles.recipe.run(
            """
            read:
            - ckan:
                host: https://catalog.wrangle.works
                dataset: test
                file: aaaaaaaaaaaaaa.csv
                api_key: ${CKAN_API_KEY}
            """
        )


def test_upload_file():
    """
    Test run action to upload a file
    """
    wrangles.recipe.run(
        """
          run:
            on_success:
              - ckan.upload:
                  host: https://catalog.wrangle.works
                  dataset: test
                  file: tests/temp/test.csv
                  api_key: ${CKAN_API_KEY}
                  output_file: test.csv

          read:
            - test:
                rows: 5
                values:
                  header: value
            
          write:
            - file:
               name: tests/temp/test.csv
        """
    )

    df = wrangles.recipe.run(
        """
          read:
            - ckan:
                host: https://catalog.wrangle.works
                dataset: test
                file: test.csv
                api_key: ${CKAN_API_KEY}
        """
    )

    assert len(df) == 5

def test_upload_files():
    """
    Test run action to upload a list of file
    """
    wrangles.recipe.run(
        """
        run:
          on_success:
            - ckan.upload:
                host: https://catalog.wrangle.works
                dataset: test
                file:
                  - tests/temp/test0.csv
                  - tests/temp/test1.csv
                api_key: ${CKAN_API_KEY}
                output_file:
                  - test0.csv
                  - test1.csv

        read:
          - test:
              rows: 5
              values:
                header0: value0
                header1: value1
            
        write:
          - file:
              name: tests/temp/test0.csv
              columns:
                - header0
          - file:
              name: tests/temp/test1.csv
              columns:
                - header1
        """
    )

    df = wrangles.recipe.run(
        """
          read:
            - concatenate:
                sources:
                  - ckan:
                      host: https://catalog.wrangle.works
                      dataset: test
                      file: test0.csv
                      api_key: ${CKAN_API_KEY}
                  - ckan:
                      host: https://catalog.wrangle.works
                      dataset: test
                      file: test1.csv
                      api_key: ${CKAN_API_KEY}
        """
    )

    assert df['header0'][0] == 'value0' and df['header1'][0] == 'value1'

def test_download_file():
    """
    Test run action to download a file
    """
    df = wrangles.recipe.run(
        """
          run:
            on_start:
              - ckan.download:
                  host: https://catalog.wrangle.works
                  dataset: test
                  file: test.csv
                  api_key: ${CKAN_API_KEY}
                  output_file: tests/temp/test.csv

          read:
            - file:
                name: tests/temp/test.csv
        """
    )

    assert len(df) > 0

def test_download_files():
    """
    Test run action to download multiple files
    """
    df = wrangles.recipe.run(
        """
          run:
            on_start:
              - ckan.download:
                  host: https://catalog.wrangle.works
                  dataset: test
                  file:
                    - test.csv
                    - test1.csv
                  api_key: ${CKAN_API_KEY}
                  output_file:
                    - tests/temp/test.csv
                    - tests/temp/test1.csv

          read:
            - union:
               sources:
                - file:
                    name: tests/temp/test.csv
                - file:
                    name: tests/temp/test1.csv
        """
    )

    assert len(df) > 0
