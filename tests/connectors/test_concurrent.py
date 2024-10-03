import wrangles
from datetime import datetime
import time

def test_concurrent():
    """
    Test the concurrent connector
    """
    save_vals = []
    def wait_and_append(df, wait):
        time.sleep(wait)
        save_vals.append(wait)
    
    start = datetime.now()

    wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: value
        write:
          - concurrent:
              write:
                - custom.wait_and_append:
                     wait: 5
                - custom.wait_and_append:
                     wait: 1
                - custom.wait_and_append:
                     wait: 3
        """,
        functions=wait_and_append
    )

    end = datetime.now()

    assert (
        (end - start).seconds < 6 and
        save_vals == [1,3,5]
    )
