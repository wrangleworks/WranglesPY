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

    def test_standardize_no_units(self):
        """
        Testing no units in text
        """
        data = pd.DataFrame({
            'input': ['My car has a mass of 190 and it holds 190 gas with a battery weight of 190']  
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
        assert df['output'][0] == ['My car has a mass of 190 and it holds 190 gas with a battery weight of 190']

    def test_santadize_empty_text(self):
        """
        Testing empty text
        """
        data = pd.DataFrame({
            'input': ['']
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
        assert df['output'][0] == ['']

    def test_standardize_unit_only(self):
        """
        Testing only units in text
        """
        data = pd.DataFrame({
            'input': ['13 feet']
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
        assert df['output'][0] == ['13 ft']


class TestUnitConversion:
    """
    Test unit conversion with standardize
    """

    def test_multiple_units(self):
        """
        Testing multiple units in text
        """
        data = pd.DataFrame({
            'input': ['My car has a mass of 190kg and it holds 190kg gas with a battery weight of 190kg']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: mass
                desiredUnit: pounds
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has a mass of 419 lb and it holds 419 lb gas with a battery weight of 419 lb']

    def test_no_units(self):
        """
        Testing no units in text
        """
        data = pd.DataFrame({
            'input': ['My car has a mass of 190 and it holds 190 pf gas with a battery weight of 190']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: mass
                desiredUnit: pounds
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has a mass of 190 and it holds 190 pf gas with a battery weight of 190']

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

    # charge
    def test_convert_and_standardize_charge(self):
        """
        Testing unit conversion
        """
        data = pd.DataFrame({
            'input': ['My car has a charge of 13 coulombs and 13lbs of weight']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: charge
                desiredUnit: millicoulombs
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has a charge of 13000 mC and 13lbs of weight']

    # current
    def test_convert_and_standardize_current(self):
        """
        Testing unit conversion
        """
        data = pd.DataFrame({
            'input': ['My car has a current of 13 amperes and 13lbs of weight']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: current
                desiredUnit: milliamperes
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has a current of 13000 mA and 13lbs of weight']


    # data transfer rate
    def test_convert_and_standardize_data_transfer_rate(self):
        """
        Testing unit conversion
        """
        data = pd.DataFrame({
            'input': ['My car has a data transfer rate of 1333333 bps and 13lbs of weight']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: data transfer rate
                desiredUnit: kilobytes per second
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has a data transfer rate of 167 kilobytes per second and 13lbs of weight']

    # electrical conductance -> siemens to kilosiemens
    def test_convert_and_standardize_electrical_conductance(self):
        """
        Testing unit conversion
        """
        data = pd.DataFrame({
            'input': ['My car has an electrical conductance of 13 siemens and 13lbs of weight']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: electrical conductance
                desiredUnit: kilosiemens
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has an electrical conductance of 0.013 kS and 13lbs of weight']

    # electrical resistance -> ohms to kiloohms
    def test_convert_and_standardize_electrical_resistance(self):
        """
        Testing unit conversion
        """
        data = pd.DataFrame({
            'input': ['My car has an electrical resistance of 13666 ohms and 13lbs of weight']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: electrical resistance
                desiredUnit: kiloohms
                sigFigs: 3
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has an electrical resistance of 13.7 kΩ and 13lbs of weight']

    # energy -> joules to kilojoules
    def test_convert_and_standardize_energy(self):
        """
        Testing unit conversion
        """
        data = pd.DataFrame({
            'input': ['My car has an energy of 13000 joules and 13lbs of weight']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: energy
                desiredUnit: kilojoules
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has an energy of 13 kJ and 13lbs of weight']

    # force -> newtons to kilonewtons
    def test_convert_and_standardize_force(self):
        """
        Testing unit conversion
        """
        data = pd.DataFrame({
            'input': ['My car has a force of 13000 newtons and 13lbs of weight']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: force
                desiredUnit: kilonewtons
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has a force of 13 kN and 13lbs of weight']

    # length
    def test_convert_and_standardize_length(self):
        """
        Testing unit conversion
        """
        data = pd.DataFrame({
            'input': ['My car has a length of 13 feet and 13lbs of weight']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: length
                desiredUnit: meters
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has a length of 3.96 m and 13lbs of weight']

    # pressure
    def test_convert_and_standardize_pressure(self):
        """
        Testing unit conversion
        """
        data = pd.DataFrame({
            'input': ['My car has a pressure of 13000 pascals and 13lbs of weight']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: pressure
                desiredUnit: kilopascals
            """,
            dataframe=data
        )
        assert df['output'][0] == ['My car has a pressure of 13 kPa and 13lbs of weight']

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
        assert df['output'][0] == ['My car has a mass of 419 lb and it holds 13 liters of gasoline with a battery of 14 volts']