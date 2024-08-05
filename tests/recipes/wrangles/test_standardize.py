import wrangles
import pandas as pd
import pytest

class TestStandardizeAttributes:
    """
    Format (standardize) attributes or remove them
    """

    def test_standardize_attributes_all(self):
        """
        Testing standardizing all attributes in text
        """
        data = pd.DataFrame({
            'input': ["My 13 foot car has a mass of 190kg and it holds 13 liters of gasoline with a battery of 14 volts"]
        })

        df = wrangles.recipe.run(
            recipe="""
            wrangles:
                - standardize.attributes:
                    input: input
                    output: output
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My 13 ft car has a mass of 190 kg and it holds 13 l of gasoline with a battery of 14 V']

    def test_standardize_attributes_non_existing_units(self):
        """
        Testing a non existent units
        """
        data = pd.DataFrame({
            'input': ["my 13 metre car has a quantonium of 13Rx and that's random 13 number"]
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
            """,
            dataframe=data
        )
        assert df['output'][0] == ["my 13 m car has a quantonium of 13Rx and that's random 13 number"]


    def test_standardize_specific_attribute_length(self):
        """
        Standardize a specific attribute in text
        Length
        """
        data = pd.DataFrame({
            'input': ["My 13 foot car has a mass of 190kg and it holds 13 liters and the wheel is 4cm wide with 10 mm of thread left"]
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: length
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My 13 ft car has a mass of 190kg and it holds 13 liters and the wheel is 4 cm wide with 10 mm of thread left']

    def test_standardize_specific_attribute_mass(self):
        """
        Standardize a specific attribute in text
        Mass
        """
        data = pd.DataFrame({
            'input': ["My 13 foot car has a mass of 190kg and it holds 13 liters and the wheel is 4cm wide with 10 mm of thread left"]
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: mass
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My 13 foot car has a mass of 190 kg and it holds 13 liters and the wheel is 4cm wide with 10 mm of thread left']

    def test_standardize_specific_attribute_volume(self):
        """
        Attribute specified not present in text
        Volume
        """
        data = pd.DataFrame({
            'input': ['My 13 foot car has a mass of 190kg and the wheel is 4cm']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: volume
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My 13 foot car has a mass of 190kg and the wheel is 4cm']

class TestUnitConversion:
    """
    Test unit conversion with standardize
    """

    # angle
    def test_convert_and_standardize_angle(self):
        """
        Testing unit conversion
        """
        data = pd.DataFrame({
            'input': ['My car has a 90 degree angle and 13lbs of weight']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: angle
                desiredUnit: radians
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has a 1.57 rad angle and 13lbs of weight']

    # area
    def test_convert_and_standardize_area(self):
        """
        Testing unit conversion
        """
        data = pd.DataFrame({
            'input': ['My car has an area of 13.666 square feet and 13lbs of weight']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: area
                desiredUnit: square meter
                sigFigs: 2
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has an area of 1.3 sq m and 13lbs of weight']

    # capacitance
    def test_convert_and_standardize_capacitance(self):
        """
        Testing unit conversion
        """
        data = pd.DataFrame({
            'input': ['My car has a capacitance of 13 farads and 13lbs of weight']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: capacitance
                desiredUnit: microfarads
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has a capacitance of 13000000 µF and 13lbs of weight']

    # Weight
    def test_covert_and_standardize_weight(self):
        """
        Testing unit conversion
        """
        data = pd.DataFrame({
            'input': ['My car has a mass of 190kg and it holds 13 liters of gasoline with a battery of 14 volts']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: weight
                desiredUnit: pounds
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has a mass of 419 lbs and it holds 3.434 gallons of gasoline with a battery of 14 V']