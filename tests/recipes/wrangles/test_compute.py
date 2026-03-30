import wrangles
import pandas as pd


class TestCaseWhen:
    """  
    Test case_when wrangle  
    """

    def test_case_when_basic(self):
        """  
        Test basic case_when functionality with simple conditions  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Match  
                  default: Weak  
                  cases:  
                    - condition: (Score > 0.84) & (Type == 'Code')  
                      value: Strong  
                    - condition: (Score > 0.60) & (Type == 'Code')  
                      value: Moderate  
            """,
            dataframe=pd.DataFrame({
                'Score': [0.9, 0.7, 0.5, 0.85],
                'Type': ['Code', 'Code', 'Code', 'Text']
            })
        )
        assert (
            df['Match'][0] == 'Strong' and
            df['Match'][1] == 'Moderate' and
            df['Match'][2] == 'Weak' and
            df['Match'][3] == 'Weak'
        )

    def test_case_when_where(self):
        """  
        Test case_when with where clause  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Result  
                  default: Default  
                  cases:  
                    - condition: col1 > 5  
                      value: High  
                    - condition: col1 > 2  
                      value: Medium  
                  where: col2 == 'A'  
            """,
            dataframe=pd.DataFrame({
                'col1': [1, 6, 3, 8],
                'col2': ['A', 'A', 'B', 'A']
            })
        )
        assert (
            df['Result'][0] == 'Default' and
            df['Result'][1] == 'High' and
            df['Result'][2] == '' and
            df['Result'][3] == 'High'
        )

    def test_case_when_numeric_output(self):
        """  
        Test case_when with numeric output values  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Score  
                  default: 0  
                  cases:  
                    - condition: Grade == 'A'  
                      value: 100  
                    - condition: Grade == 'B'  
                      value: 80  
                    - condition: Grade == 'C'  
                      value: 60  
            """,
            dataframe=pd.DataFrame({
                'Grade': ['A', 'B', 'C', 'D']
            })
        )
        assert (
            df['Score'][0] == 100 and
            df['Score'][1] == 80 and
            df['Score'][2] == 60 and
            df['Score'][3] == 0
        )

    def test_case_when_multiple_conditions(self):
        """  
        Test case_when with complex multiple conditions  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Category  
                  default: Other  
                  cases:  
                    - condition: (Price > 100) & (Stock > 50)  
                      value: Premium High Stock  
                    - condition: (Price > 100) & (Stock <= 50)  
                      value: Premium Low Stock  
                    - condition: (Price <= 100) & (Stock > 50)  
                      value: Budget High Stock  
            """,
            dataframe=pd.DataFrame({
                'Price': [150, 150, 50, 50],
                'Stock': [60, 30, 60, 30]
            })
        )
        assert (
            df['Category'][0] == 'Premium High Stock' and
            df['Category'][1] == 'Premium Low Stock' and
            df['Category'][2] == 'Budget High Stock' and
            df['Category'][3] == 'Other'
        )

    def test_case_when_if_condition(self):
        """  
        Test case_when with if statement  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Result  
                  default: 'No'
                  cases:  
                    - condition: value > 5  
                      value: 'Yes'
                  if: ${run_wrangle}  
            """,
            dataframe=pd.DataFrame({
                'value': [3, 7, 2]
            }),
            variables={'run_wrangle': True}
        )
        assert df['Result'][0] == 'No' and df['Result'][1] == 'Yes'

    def test_case_when_if_false(self):
        """  
        Test case_when skipped when if condition is false  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Result  
                  default: No  
                  cases:  
                    - condition: value > 5  
                      value: Yes  
                  if: ${run_wrangle}  
            """,
            dataframe=pd.DataFrame({
                'value': [3, 7, 2]
            }),
            variables={'run_wrangle': False}
        )
        assert 'Result' not in df.columns

    def test_case_when_empty_dataframe(self):
        """  
        Test case_when with empty dataframe  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Result  
                  default: Default  
                  cases:  
                    - condition: col1 > 5  
                      value: High  
            """,
            dataframe=pd.DataFrame({'col1': []})
        )
        assert df.empty and 'Result' in df.columns

    def test_case_when_string_conditions(self):
        """  
        Test case_when with string comparison conditions  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Status  
                  default: Unknown  
                  cases:  
                    - condition: Name == 'Alice'  
                      value: Admin  
                    - condition: Name == 'Bob'  
                      value: User  
            """,
            dataframe=pd.DataFrame({
                'Name': ['Alice', 'Bob', 'Charlie']
            })
        )
        assert (
            df['Status'][0] == 'Admin' and
            df['Status'][1] == 'User' and
            df['Status'][2] == 'Unknown'
        )

    def test_case_when_no_default(self):
        """
        Test case_when without default on a new column - unmatched rows are empty string
        (the recipe framework converts NaN to '' after each wrangle).
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Result  
                  cases:  
                    - condition: value > 5  
                      value: High  
            """,
            dataframe=pd.DataFrame({
                'value': [3, 7, 2]
            })
        )

        assert (
            df['Result'][0] == '' and
            df['Result'][1] == 'High' and
            df['Result'][2] == ''
        )

    def test_case_when_no_default_preserves_existing(self):
        """
        Test case_when without default on an existing column -
        unmatched rows keep their original values.
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - compute.case_when:
                  output: label
                  cases:
                    - condition: value > 5
                      value: High
            """,
            dataframe=pd.DataFrame({
                'value': [3, 7, 2],
                'label': ['original_a', 'original_b', 'original_c']
            })
        )

        assert (
            df['label'][0] == 'original_a' and
            df['label'][1] == 'High' and
            df['label'][2] == 'original_c'
        )

    def test_case_when_order_matters(self):
        """  
        Test that case_when evaluates conditions in order (first match wins)  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Category  
                  default: Low  
                  cases:  
                    - condition: value > 8  
                      value: Very High  
                    - condition: value > 5  
                      value: High  
                    - condition: value > 2  
                      value: Medium  
            """,
            dataframe=pd.DataFrame({
                'value': [1, 3, 6, 9]
            })
        )
        assert (
            df['Category'][0] == 'Low' and
            df['Category'][1] == 'Medium' and
            df['Category'][2] == 'High' and
            df['Category'][3] == 'Very High'
        )

    def test_case_when_with_variables(self):
        """  
        Test case_when with template variables in conditions  
        """
        df = wrangles.recipe.run(
            """  
            wrangles:  
              - compute.case_when:  
                  output: Result  
                  default: Low  
                  cases:  
                    - condition: value > ${threshold}  
                      value: High  
            """,
            dataframe=pd.DataFrame({
                'value': [3, 7, 2]
            }),
            variables={'threshold': 5}
        )
        assert df['Result'][0] == 'Low' and df['Result'][1] == 'High'

    def test_case_when_column_with_space(self):
        """
        Test case_when with template variables in conditions 
        where a column name includes a space
            """
        df = pd.DataFrame({
            "My Column": [1, 2, 3],
            "Other Column": [4, 5, 6]
        })
        recipe = """
        wrangles:
            - compute.case_when:
                output: Result
                cases:
                    - condition: My_Column == 1
                      value: "One"
                    - condition: My_Column == 2
                      value: "Two"
                    - condition: My_Column == 3
                      value: "Three"
            """
        result = wrangles.recipe.run(recipe, dataframe=df)

        assert result["Result"].tolist() == ["One", "Two", "Three"]

    def test_case_when_and_two_columns(self):
        """
        Test case_when with an 'and' condition across two columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - compute.case_when:
                  output: Result
                  default: Other
                  cases:
                    - condition: score >= 80 and grade == 'A'
                      value: Top
                    - condition: score >= 60 and grade == 'B'
                      value: Good
            """,
            dataframe=pd.DataFrame({
                'score': [90, 65, 90, 50],
                'grade': ['A', 'B', 'C', 'C'],
            })
        )
        assert df['Result'].tolist() == ['Top', 'Good', 'Other', 'Other']

    def test_case_when_or_two_columns(self):
        """
        Test case_when with an 'or' condition across two columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - compute.case_when:
                  output: Flag
                  default: Normal
                  cases:
                    - condition: score > 90 or status == 'vip'
                      value: Priority
            """,
            dataframe=pd.DataFrame({
                'score': [95, 50, 70],
                'status': ['regular', 'vip', 'regular'],
            })
        )
        assert df['Flag'].tolist() == ['Priority', 'Priority', 'Normal']

    def test_case_when_and_or_combined(self):
        """
        Test case_when with combined 'and'/'or' logic across multiple columns
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - compute.case_when:
                  output: Label
                  default: None
                  cases:
                    - condition: (age >= 18 and income > 50000) or vip == True
                      value: Eligible
                    - condition: age < 18 or income <= 20000
                      value: Ineligible
            """,
            dataframe=pd.DataFrame({
                'age':    [25, 30, 15, 20],
                'income': [60000, 30000, 10000, 55000],
                'vip':    [False, True, False, False],
            })
        )
        assert df['Label'].tolist() == ['Eligible', 'Eligible', 'Ineligible', 'Eligible']

    def test_case_when_boolean_column(self):
        """
        Test case_when conditions using boolean columns directly
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - compute.case_when:
                  output: Access
                  default: Denied
                  cases:
                    - condition: is_admin == True
                      value: Admin
                    - condition: is_active == True
                      value: User
            """,
            dataframe=pd.DataFrame({
                'is_admin':  [True, False, False],
                'is_active': [False, True, False],
            })
        )
        assert df['Access'].tolist() == ['Admin', 'User', 'Denied']

    def test_case_when_boolean_not(self):
        """
        Test case_when condition using boolean negation
        """
        df = wrangles.recipe.run(
            """
            wrangles:
              - compute.case_when:
                  output: Status
                  default: Active
                  cases:
                    - condition: is_deleted == True
                      value: Deleted
                    - condition: is_deleted == False and is_paused == True
                      value: Paused
            """,
            dataframe=pd.DataFrame({
                'is_deleted': [False, True, False],
                'is_paused':  [False, False, True],
            })
        )
        assert df['Status'].tolist() == ['Active', 'Deleted', 'Paused']
