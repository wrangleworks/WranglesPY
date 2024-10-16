import pandas as pd
import os
import wrangles
import pytest
import time

s3_key = os.getenv('AWS_ACCESS_KEY_ID', '...')
s3_secret = os.getenv('AWS_SECRET_ACCESS_KEY', '...')

class TestRead:
    """
    Test reading from an S3 bucket
    within the read of a recipe
    """
    def test_read_named_credentials(self):
        """
        Reading a file in S3 using
        credentials passed as parameters
        """
        df = wrangles.recipe.run(
            """
            read:
            - s3:
                bucket: wrwx-public
                key: World Cup Winners.xlsx
                access_key: ${s3_key}
                secret_access_key: ${s3_secret}
            """,
            variables={
                's3_key': s3_key,
                's3_secret': s3_secret
            }
        )
        assert df.iloc[0]['Winners'] == 'Uruguay'

    def test_read_env_variables(self):
        """
        Test reading a file using credentials
        passed as environment variables
        """
        df = wrangles.recipe.run(
            """
            read:
            - s3:
                bucket: wrwx-public
                key: World Cup Winners.xlsx
            """
        )
        assert df.iloc[0]['Winners'] == 'Uruguay'

    def test_read_error_invalid_file(self):
        """
        Test that a clear error is raised if the file is missing
        """
        with pytest.raises(FileNotFoundError, match="File not found"):
            wrangles.recipe.run(
                """
                read:
                - s3:
                    bucket: wrwx-public
                    key: does_not_exist.csv
                """
            )

    def test_read_error_invalid_bucket(self):
        """
        Test that a clear error is raised if the bucket isn't valid
        """
        with pytest.raises(RuntimeError, match="bucket does not exist"):
            wrangles.recipe.run(
                """
                read:
                - s3:
                    bucket: wrwx-does-not-exist
                    key: does_not_exist.csv
                """
            )

    def test_read_gzip(self):
        """
        Test reading a gzipped file
        """
        # Download and verify it matches
        df = wrangles.recipe.run(
            """
            read:
            - s3:
                bucket: wrwx-public
                key: test_gzip_read.csv.gz
            """
        )
        assert df['header'][0] == 'Sed magnam tempora adipisci velit eius consectetur'

    def test_read_error_invalid_credentials(self):
        """
        Test that a clear error is raised if the credentials aren't correct
        """
        with pytest.raises(RuntimeError, match="Access Key Id you provided does not exist"):
            wrangles.recipe.run(
                """
                read:
                - s3:
                    bucket: wrwx-public
                    key: World Cup Winners.xlsx
                    access_key: not_a_valid_key
                    secret_access_key: not_a_valid_secret
                """
            )

class TestWrite:
    """
    Test writing directly to S3
    """
    def test_write_credentials_parameters(self):
        """
        Writing to an S3 file using
        credentials passed as parameters
        """
        df = wrangles.recipe.run(
            """
            write:
            - s3:
                bucket: wrwx-public
                key: World Cup Titles.xlsx
                access_key: ${s3_key}
                secret_access_key: ${s3_secret}
            """,
            variables={
                's3_key': s3_key,
                's3_secret': s3_secret
            },
            dataframe=pd.DataFrame({
                'Country': ['Brazil', 'Germany', 'Italy'],
                'Titles': [5, 4, 4,],
            })
        )
        assert df.iloc[0]['Country'] == 'Brazil'

    def test_write_env_variables(self):
        """
        Writing using credentials passed as
        environment variables
        """
        df = wrangles.recipe.run(
            """
            write:
            - s3:
                bucket: wrwx-public
                key: World Cup Titles.xlsx
            """,
            dataframe=pd.DataFrame({
                'Country': ['Brazil', 'Germany', 'Italy'],
                'Titles': [5, 4, 4,],
            })
        )
        assert df.iloc[0]['Country'] == 'Brazil'
    
    def test_write_error_invalid_bucket(self):
        """
        Test that a clear error is raised if the bucket isn't valid
        """
        with pytest.raises(RuntimeError, match="bucket does not exist"):
            wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 100
                    values:
                        header: <sentence>
                write:
                - s3:
                    bucket: wrwx-does-not-exist
                    key: does_not_exist.csv
                """
            )

    def test_write_error_invalid_credentials(self):
        """
        Test that a clear error is raised if the credentials aren't correct
        """
        with pytest.raises(RuntimeError, match="Access Key Id you provided does not exist"):
            wrangles.recipe.run(
                """
                read:
                - test:
                    rows: 100
                    values:
                        header: <sentence>
                write:
                - s3:
                    bucket: wrwx-does-not-exist
                    key: does_not_exist.csv
                    access_key: not_a_valid_key
                    secret_access_key: not_a_valid_secret
                """
            )

    def test_write_gzip(self):
        """
        Test writing a gzipped file
        """
        wrangles.recipe.run(
            """
            read:
            - test:
                rows: 100
                values:
                    header: <sentence>
            write:
            - s3:
                bucket: wrwx-public
                key: test_gzip_write.csv.gz
            """
        )


class TestRunUpload:
    """
    Test run s3.upload_files
    """
    def test_upload_error(self):
        """
        Test that an appropriate error is shown if the number of keys and filenames
        are not equal when attempting to upload files
        """
        with pytest.raises(ValueError, match="equal number of files and keys"):
            wrangles.recipe.run(
                """
                run:
                  on_start:
                    - s3.upload_files:
                        bucket: wrwx-public
                        file:
                        - tests/samples/data.csv
                        - tests/samples/data.json
                        key:
                        - Test_Upload_File.csv
                """
            )

    def test_run_upload_error_invalid_bucket(self):
        """
        Test that a clear error is raised if the bucket isn't valid
        """
        with pytest.raises(RuntimeError, match="Failed to write"):
            wrangles.recipe.run(
                """
                run:
                  on_start:
                    - s3.upload_files:
                        bucket: wrwx-does-not-exist
                        key: does_not_exist.csv
                        file: tests/samples/data.csv
                """
            )

    def test_file_upload_and_download_1(self):
        """
        Upload file to s3 key and file not included
        """
        recipe = f"""
        run:
          on_start:
            - s3.upload_files:
                bucket: wrwx-public
                file: tests/samples/data.csv
                aws_access_key_id: {s3_key}
                aws_secret_access_key: {s3_secret}
        """
        wrangles.recipe.run(recipe)
        time.sleep(3)
        # Reading uploaded file to complete the cycle
        recipe2 = f"""
        run:
          on_start:
            - s3.download_files:
                bucket: wrwx-public
                key: data.csv
                file: tests/temp/data.csv
                aws_access_key_id: {s3_key}
                aws_secret_access_key: {s3_secret}
        read:
        - file:
            name: tests/temp/data.csv
        """
        
        df = wrangles.recipe.run(recipe2)
        assert df.iloc[0]['Find'] == 'BRG'
        
    # Key and file included
    def test_file_upload_and_download_2(self):
        recipe = f"""
        run:
          on_start:
            - s3.upload_files:
                bucket: wrwx-public
                key: Test_Upload_File.csv
                file: tests/samples/data.csv
                aws_access_key_id: {s3_key}
                aws_secret_access_key: {s3_secret}
        """
        wrangles.recipe.run(recipe)
        time.sleep(3)
        # Reading uploaded file to complete the cycle
        recipe2 = f"""
        run:
          on_start:
            - s3.download_files:
                bucket: wrwx-public
                key: Test_Upload_File.csv
                file: tests/temp/temp_download_data.csv
                aws_access_key_id: {s3_key}
                aws_secret_access_key: {s3_secret}
        read:
        - file:
            name: tests/temp/temp_download_data.csv
        """
        
        df = wrangles.recipe.run(recipe2)
        assert df.iloc[0]['Find'] == 'BRG'

class TestRunDownload:
    """
    Test using run s3.download_files
    """
    def test_run_download_error_invalid_file(self):
        """
        Test that a clear error is raised if the file is missing
        """
        with pytest.raises(FileNotFoundError, match="File not found"):
            wrangles.recipe.run(
                """
                run:
                  on_start:
                    - s3.download_files:
                        bucket: wrwx-public
                        key: does_not_exist.csv
                """
            )

    def test_run_download_error_invalid_bucket(self):
        """
        Test that a clear error is raised if the bucket isn't valid
        """
        with pytest.raises(FileNotFoundError, match="File not found"):
            wrangles.recipe.run(
                """
                run:
                  on_start:
                    - s3.download_files:
                        bucket: wrwx-does-not-exist
                        key: does_not_exist.csv
                """
            )

    def test_run_download_error_invalid_credentials(self):
        """
        Test that a clear error is raised if the credentials aren't correct
        """
        with pytest.raises(PermissionError, match="Permission denied"):
            wrangles.recipe.run(
                """
                run:
                  on_start:
                    - s3.download_files:
                        bucket: wrwx-public
                        key: World Cup Winners.xlsx
                        aws_access_key_id: not_a_valid_key
                        aws_secret_access_key: not_a_valid_secret
                """
            )

    def test_download_error(self):
        """
        Downloading multiple files error
        """
        with pytest.raises(ValueError, match="equal number of keys and files"):
            wrangles.recipe.run(
                """
                run:
                  on_success:
                    - s3.download_files:
                        bucket: wrwx-public
                        key:
                        - Test_Upload_File.csv
                        - World Cup Titles.csv
                        file:
                        - tests/temp/temp_download_data.csv
                """
            )
