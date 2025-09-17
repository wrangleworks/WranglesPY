import wrangles
import pandas as pd


class TestCompareText:
    """
    Test compare.text
    """
    def test_compare_text_default(self):
        """
        Test normal Compare Text. Difference (default)
        """
        data = pd.DataFrame({
        'col1': [
            'Mario Oak Wood White Marble Top Bookshelf',
            'Luigi Oak Wood White Marble Top Coffee Table',
            'Peach Oak Wood White Marble Top Console Table',
        ],
        'col2': [
            'Mario Pine Wood Black Marble Bottom Bookshelf',
            'Luigi Maple Wood Orange Steel Top Coffee Table',
            'Peach Normal Wood Blue Plastic Top Console Table',
        ]
        })

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: difference
        """

        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df['output'].values.tolist() == ['Pine Black Bottom', 'Maple Orange Steel', 'Normal Blue Plastic']

    def test_compare_test_difference_simple_words(self):
        """
        Test with simple words
        """
        data = pd.DataFrame({
        'col1': [
            'Mario',
            'Luigi',
        ],
        'col2': [
            'Super Mario',
            'Super Luigi',
        ]
        })

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: difference
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df['output'].values.tolist() == ['Super', 'Super']

    def test_compare_text_intersection(self):
        """
        Test normal Compare Text. Intersection
        """
        data = pd.DataFrame({
        'col1': [
            'Mario Oak Wood White Marble Top Bookshelf',
            'Luigi Oak Wood White Marble Top Coffee Table',
            'Peach Oak Wood White Marble Top Console Table',
        ],
        'col2': [
            'Mario Pine Wood Black Marble Bottom Bookshelf',
            'Luigi Maple Wood Orange Steel Top Coffee Table',
            'Peach Normal Wood Blue Plastic Top Console Table',
        ]
        })

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: intersection
        """

        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df['output'].values.tolist() == ['Mario Wood Marble Bookshelf', 'Luigi Wood Top Coffee Table', 'Peach Wood Top Console Table']

    def test_compare_text_intersection_simple_words(self):
        """
        Test with simple words
        """
        data = pd.DataFrame({
        'col1': [
            'Mario',
            'Luigi',
        ],
        'col2': [
            'Super Mario',
            'Super Luigi',
        ]
        })

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: intersection
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df['output'].values.tolist() == ['Mario', 'Luigi']

    def test_compare_text_empty_value_second_column(self):
        """
        Having an empty value in second column
        """
        data = pd.DataFrame({
        'col1': [
            'Mario Oak Wood White Marble Top Bookshelf',
            'Peach Oak Wood White Marble Top Console Table',
        ],
        'col2': [
            'Mario Pine Wood Black Marble Bottom Bookshelf',
            '',
        ]
        })

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: intersection
        """

        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df['output'].values.tolist() == ['Mario Wood Marble Bookshelf', '']

    def test_compare_text_intersection_multiple_columns(self):
        """
        Test intersection with more than two columns
        """
        data = pd.DataFrame({
            'col1': ['mario', 'luigi', 'peach', 'toad'],
            'col2': ['super mario', 'super luigi', 'super peach', 'super toad'],
            'col3': ['mega mario', 'mega luigi', 'mega peach', 'mega toad'],
        })
        recipe = """
        wrangles:
        - compare.text:
            input:
                - col1
                - col2
                - col3
            output: output
            method: intersection
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['output'].values.tolist() == ['mario', 'luigi', 'peach', 'toad']

    def test_compare_text_intersection_empty_values(self):
        """
        Having empty values in the columns
        """
        data = pd.DataFrame({
        'col1': [
            'Mario',
            'Luigi',
            '',
            'Bowser',
            ''
        ],
        'col2': [
            'Super Mario',
            'Super Luigi',
            'Super Peach',
            '',
            ''
        ]
        })

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: intersection
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df['output'].values.tolist() == ['Mario', 'Luigi', '', '', '']

    def test_compare_text_difference_multiple_columns(self):
        """
        Test difference with more than two columns
        """
        data = pd.DataFrame({
            'col1': ['mario', 'luigi', 'peach', 'toad'],
            'col2': ['super mario', 'super luigi', 'super peach', 'super toad'],
            'col3': ['mega mario', 'mega luigi', 'mega peach', 'mega toad'],
        })
        recipe = """
        wrangles:
        - compare.text:
            input:
                - col1
                - col2
                - col3
            output: output
            method: difference
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert all(x=='super mega' for x in df['output'].values.tolist())

    def test_compare_text_difference_empty_values(self):
        """
        Having empty values in the columns
        """
        data = pd.DataFrame({
        'col1': [
            'Mario',
            'Luigi',
            '',
            'Bowser',
            ''
        ],
        'col2': [
            'Super Mario',
            'Super Luigi',
            'Super Peach',
            '',
            ''
        ]
        })

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: difference
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df['output'].values.tolist() == ['Super', 'Super', 'Super Peach', '', '']

    def test_compare_text_empty_value_first_column(self):
        """
        Having an empty value in the first column should return the whole value of the second column
        """
        data = pd.DataFrame({
        'col1': [
            'Mario Oak Wood White Marble Top Bookshelf',
            '',
        ],
        'col2': [
            'Mario Pine Wood Black Marble Bottom Bookshelf',
            'Peach Oak Wood White Marble Top Console Table',
        ]
        })

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
        """

        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df['output'].values.tolist() == ['Pine Black Bottom', 'Peach Oak Wood White Marble Top Console Table']

    def test_compare_text_overlap(self):
        """
        Using overlap method
        """
        data = pd.DataFrame({
        'col1': [
            'Mario',
            'Luigi',
        ],
        'col2': [
            'SuperMario',
            'SuperLuigi',
        ]
        })

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: overlap
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df['output'].values.tolist() == ['*****Mario', '*****Luigi']

    def test_compare_text_overlap_empty_values(self):
        """
        Using overlap method and having empty values
        """
        data = pd.DataFrame({
        'col1': [
            'Mario',
            'Luigi',
            '',
            'Bowser',
            ''
        ],
        'col2': [
            'SuperMario',
            'SuperLuigi',
            'SuperPeach',
            '',
            ''
        ]
        })

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: overlap
            non_match_char: '@'
            include_ratio: True
            decimal_places: 2
            exact_match: 'They are the same'
            empty_a: 'Empty A'
            empty_b: 'Empty B'
            all_empty: 'Both Empty'
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df['output'].values.tolist() == [['@@@@@Mario', 0.67], ['@@@@@Luigi', 0.67], ['Empty A', 0], ['Empty B', 0], ['Both Empty', 0]]

    def test_compare_text_overlap_include_ratio(self):
        """
        Using overlap method and including the ratio
        """
        data = pd.DataFrame({
        'col1': [
            'Mario',
            'Luigi',
            'Mario',
            'Luigi',
        ],
        'col2': [
            'Mario',
            'Luigi',
            'Martio',
            'Luiigi',
        ]
        })

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: overlap
            include_ratio: True
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )

        assert df['output'].values.tolist() == [['Mario', 1], ['Luigi', 1], ['Mar*io', 0.909], ['Lui*gi', 0.909]]

    def test_compare_overlap_default_settings(self):
        """
        Using overlap method and using the default empty values
        """
        data = pd.DataFrame({
        'col1': [
            'Mario',
            'Luigi',
            '',
            'Bowser',
            ''
        ],
        'col2': [
            'SuperMario',
            'SuperLuigi',
            'SuperPeach',
            '',
            ''
        ]
        })

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: overlap
        """
        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df['output'].values.tolist() == ['*****Mario', '*****Luigi', '', '', '']

    def test_compare_text_where(self):
        """
        Test Compare Text using where
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - compare.text:
                input:
                - col1
                - col2
                output: output
                method: difference
                where: col3 == 'Yes'
            """,
            dataframe=pd.DataFrame({
                'col1': [
                    'Mario Oak Wood White Marble Top Bookshelf',
                    'Luigi Oak Wood White Marble Top Coffee Table',
                    'Peach Oak Wood White Marble Top Console Table',
                ],
                'col2': [
                    'Mario Pine Wood Black Marble Bottom Bookshelf',
                    'Luigi Maple Wood Orange Steel Top Coffee Table',
                    'Peach Normal Wood Blue Plastic Top Console Table',
                ],
                'col3': [
                    'Yes',
                    'No',
                    'Yes'
                ]
            }),
        )
        assert (
            df['output'][0] == 'Pine Black Bottom' and
            df['output'][1] == '' and
            df['output'][2] == 'Normal Blue Plastic'
        )

    def test_compare_text_where_empty_values(self):
        """
        Test Compare Text with empty dataframe
        """
        df = wrangles.recipe.run(
            """
            wrangles:
            - compare.text:
                input:
                - col1
                - col2
                output: output
                method: difference
            """,
            dataframe=pd.DataFrame({
                'col1': [],
                'col2': [],
                'col3': []
            }),
        )
        
        assert df.empty and df.columns.to_list() == ['col1', 'col2', 'col3', 'output']

    def test_compare_text_case_insensitive_difference(self):
        """
        Test compare using case insensitive difference
        """
        data = pd.DataFrame({
        'col1': [
            'THIS IS IN ALL CAPS',
            'ANOTHER LINE THAT IS ALSO IN CAPS',
            'YET ANOTHER LINE IN CAPS',
        ],
        'col2': [
            'this is in all lowercase',
            'another line that is also in lowercase',
            'yet another line in lowercase',
        ]
        })

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: difference
            case_sensitive: false
        """

        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df['output'].values.tolist() == ['lowercase', 'lowercase', 'lowercase']

    def test_compare_text_case_insensitive_intersection(self):
        """
        Test compare using case insensitive intersection
        """
        data = pd.DataFrame({
        'col1': [
            'THIS IS IN ALL CAPS',
            'ANOTHER LINE THAT IS ALSO IN CAPS',
            'YET ANOTHER LINE IN CAPS',
        ],
        'col2': [
            'this is in all lowercase',
            'another line that is also in lowercase',
            'yet another line in lowercase',
        ]
        })

        recipe = """
        wrangles:
        - compare.text:
            input:
            - col1
            - col2
            output: output
            method: intersection
            case_sensitive: false
        """

        df = wrangles.recipe.run(
            recipe=recipe,
            dataframe=data,
        )
        assert df['output'].values.tolist() == ['THIS IS IN ALL', 'ANOTHER LINE THAT IS ALSO IN', 'YET ANOTHER LINE IN']