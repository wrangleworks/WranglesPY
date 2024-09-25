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

    def test_standardize_unit_sigFigs(self):
        """
        Testing only units in text
        """
        data = pd.DataFrame({
            'input': ['13.999999 feet of hiking trail']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: length
                desiredUnit: meters
                sigFigs: 2
            """,
            dataframe=data
        )
        assert df['output'][0] == ['4.3 m of hiking trail']

    def test_standardize_unit_sigFigs_same_unit(self):
        """
        Testing only units in text
        """
        data = pd.DataFrame({
            'input': ['13.999999 feet of hiking trail']
        })
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - standardize.attributes:
                input: input
                output: output
                attribute_type: length
                desiredUnit: feet
                sigFigs: 2
            """,
            dataframe=data
        )
        assert df['output'][0] == ['14 ft of hiking trail']


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


#
# Standardize Custom
#
class TestStandardizeCustom:
    """
    Legacy and new standardize tests (new module)
    """
    def test_standardize_1(self):
        data = pd.DataFrame({
        'Abbrev': ['ASAP', 'ETA'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations'] == 'As Soon As Possible'

    def test_standardize_1_new_module(self):
        data = pd.DataFrame({
        'Abbrev': ['ASAP', 'ETA'],
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: Abbrev
                output: Abbreviations
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations'] == 'As Soon As Possible'
        
    # Missing ${ } in model_id
    def test_standardize_2(self):
        data = pd.DataFrame({
        'Abbrev': ['ASAP'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                model_id: wrong_model
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Incorrect model_id. May be missing "${ }" around value' in info.value.args[0]
        )

    def test_standardize_2_new_module(self):
        data = pd.DataFrame({
        'Abbrev': ['ASAP'],
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: Abbrev
                output: Abbreviations
                model_id: wrong_model
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Incorrect model_id. May be missing "${ }" around value' in info.value.args[0]
        )

    # Missing a character in model_id format
    def test_standardize_3(self):
        data = pd.DataFrame({
        'Abbrev': ['ASAP'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                model_id: 6c4ab44-8c66-40e8
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX' in info.value.args[0]
        )

    def test_standardize_3_new_module(self):
        data = pd.DataFrame({
        'Abbrev': ['ASAP'],
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: Abbrev
                output: Abbreviations
                model_id: 6c4ab44-8c66-40e8
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX' in info.value.args[0]
        )

    # using an extract model with standardize function
    def test_standardize_4(self):
        data = pd.DataFrame({
        'Abbrev': ['ASAP'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                model_id: 1eddb7e8-1b2b-4a52
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Using extract model_id 1eddb7e8-1b2b-4a52 in a standardize function.' in info.value.args[0]
        )

    def test_standardize_4_new_module(self):
        data = pd.DataFrame({
        'Abbrev': ['ASAP'],
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: Abbrev
                output: Abbreviations
                model_id: 1eddb7e8-1b2b-4a52
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Using extract model_id 1eddb7e8-1b2b-4a52 in a standardize function.' in info.value.args[0]
        )
        
    # Using classify model with standardize function
    def test_standardize_5(self):
        data = pd.DataFrame({
        'Abbrev': ['ASAP'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                model_id: a62c7480-500e-480c
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Using classify model_id a62c7480-500e-480c in a standardize function.' in info.value.args[0]
        )

    def test_standardize_5_new_module(self):
        data = pd.DataFrame({
        'Abbrev': ['ASAP'],
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: Abbrev
                output: Abbreviations
                model_id: a62c7480-500e-480c
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Using classify model_id a62c7480-500e-480c in a standardize function.' in info.value.args[0]
        )

    def test_standardize_where(self):
        """
        Test standardize function using a where clause
        """
        data = pd.DataFrame({
        'Product': ['Wrench', 'Hammer', 'Pliers'],
        'Price': [4.99, 9.99, 14.99]
        })
        recipe = """
        wrangles:
            - standardize:
                input: Product
                output: Product Standardized
                model_id: 6ca4ab44-8c66-40e8
                where: Price > 10
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Product Standardized'] == "" and df.iloc[2]['Product Standardized'] == 'Pliers'

    def test_standardize_where_new_module(self):
        """
        Test standardize function using a where clause
        """
        data = pd.DataFrame({
        'Product': ['Wrench', 'Hammer', 'Pliers'],
        'Price': [4.99, 9.99, 14.99]
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: Product
                output: Product Standardized
                model_id: 6ca4ab44-8c66-40e8
                where: Price > 10
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Product Standardized'] == "" and df.iloc[2]['Product Standardized'] == 'Pliers'

    # List of inputs to one output
    def test_standardize_multi_input_single_output(self):
        """
        Test error using multiple input columns and only one output
        """
        data = pd.DataFrame({
        'Abbrev1': ['ASAP'],
        'Abbrev2': ['RSVP']
        })
        recipe = """
        wrangles:
            - standardize:
                input: 
                - Abbrev1
                - Abbrev2
                output: Abbreviations
                model_id: 6ca4ab44-8c66-40e8
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    def test_standardize_multi_input_single_output_new_module(self):
        """
        Test error using multiple input columns and only one output
        """
        data = pd.DataFrame({
        'Abbrev1': ['ASAP'],
        'Abbrev2': ['RSVP']
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: 
                - Abbrev1
                - Abbrev2
                output: Abbreviations
                model_id: 6ca4ab44-8c66-40e8
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'The lists for input and output must be the same length.' in info.value.args[0]
        )

    # List of inputs and outputs single model_id
    def test_standardize_multi_io_single_model(self):
        """
        Test output using multiple input and output columns with a single model_id
        """
        data = pd.DataFrame({
        'Abbrev1': ['ASAP'],
        'Abbrev2': ['ETA']
        })
        recipe = """
        wrangles:
            - standardize:
                input: 
                - Abbrev1
                - Abbrev2
                output: 
                - Abbreviations1
                - Abbreviations2
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations1'] == 'As Soon As Possible' and df.iloc[0]['Abbreviations2'] == 'Estimated Time of Arrival'

    def test_standardize_multi_io_single_model_new_module(self):
        """
        Test output using multiple input and output columns with a single model_id
        """
        data = pd.DataFrame({
        'Abbrev1': ['ASAP'],
        'Abbrev2': ['ETA']
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: 
                - Abbrev1
                - Abbrev2
                output: 
                - Abbreviations1
                - Abbreviations2
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations1'] == 'As Soon As Possible' and df.iloc[0]['Abbreviations2'] == 'Estimated Time of Arrival'

    # List of inputs and outputs single model_id with where
    def test_standardize_multi_io_single_model_where(self):
        """
        Test output using multiple input and output columns with a single model_id with a where filter
        """
        data = pd.DataFrame({
        'Abbrev1': ['FOMO', 'IDK', 'ASAP', 'ETA'],
        'Abbrev2': ['IDK', 'FOMO', 'ASAP', 'ETA']
        })
        recipe = """
        wrangles:
            - standardize:
                input: 
                - Abbrev1
                - Abbrev2
                output: 
                - Abbreviations1
                - Abbreviations2
                model_id: 6ca4ab44-8c66-40e8
                where: Abbrev1 LIKE Abbrev2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations1'] == "" and df.iloc[2]['Abbreviations1'] == 'As Soon As Possible'

    # List of inputs and outputs single model_id with where
    def test_standardize_multi_io_single_model_where_new_module(self):
        """
        Test output using multiple input and output columns with a single model_id with a where filter
        """
        data = pd.DataFrame({
        'Abbrev1': ['FOMO', 'IDK', 'ASAP', 'ETA'],
        'Abbrev2': ['IDK', 'FOMO', 'ASAP', 'ETA']
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: 
                - Abbrev1
                - Abbrev2
                output: 
                - Abbreviations1
                - Abbreviations2
                model_id: 6ca4ab44-8c66-40e8
                where: Abbrev1 LIKE Abbrev2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations1'] == "" and df.iloc[2]['Abbreviations1'] == 'As Soon As Possible'

    def test_standardize_case_sensitive(self):
        """
        Test standardize with case sensitivity
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                case_sensitive: true
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations'] == 'asap' and df.iloc[1]['Abbreviations'] == 'eta'

    def test_standardize_case_sensitive_new_module(self):
        """
        Test standardize with case sensitivity
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta'],
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: Abbrev
                output: Abbreviations
                case_sensitive: true
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations'] == 'asap' and df.iloc[1]['Abbreviations'] == 'eta'

    def test_standardize_case_insensitive(self):
        """
        Test standardize with case insensitivity
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                case_sensitive: false
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations'] == 'As Soon As Possible' and df.iloc[1]['Abbreviations'] == 'Estimated Time of Arrival'

    def test_standardize_case_insensitive_new_module(self):
        """
        Test standardize with case insensitivity
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta'],
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: Abbrev
                output: Abbreviations
                case_sensitive: false
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations'] == 'As Soon As Possible' and df.iloc[1]['Abbreviations'] == 'Estimated Time of Arrival'

    def test_standardize_case_default(self):
        """
        Test standardize with case default
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: Abbreviations
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations'] == 'As Soon As Possible' and df.iloc[1]['Abbreviations'] == 'Estimated Time of Arrival'

    def test_standardize_case_default_new_module(self):
        """
        Test standardize with case default
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta'],
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: Abbrev
                output: Abbreviations
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbreviations'] == 'As Soon As Possible' and df.iloc[1]['Abbreviations'] == 'Estimated Time of Arrival'

    def test_standardize_case_sensitive_multiple_rows(self):
        """
        Test standardize with case sensitive and multiple inputs and outputs
        """
        data = pd.DataFrame({
        'Abbrev1': ['asap'],
        'Abbrev2': ['eta']
        })
        recipe = """
        wrangles:
            - standardize:
                input: 
                - Abbrev1
                - Abbrev2
                output: 
                - Abbrev1 output
                - Abbrev2 output
                case_sensitive: true
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbrev1 output'] == 'asap' and df.iloc[0]['Abbrev2 output'] == 'eta'

    def test_standardize_case_sensitive_multiple_rows_new_module(self):
        """
        Test standardize with case sensitive and multiple inputs and outputs
        """
        data = pd.DataFrame({
        'Abbrev1': ['asap'],
        'Abbrev2': ['eta']
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: 
                - Abbrev1
                - Abbrev2
                output: 
                - Abbrev1 output
                - Abbrev2 output
                case_sensitive: true
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbrev1 output'] == 'asap' and df.iloc[0]['Abbrev2 output'] == 'eta'

    def test_standardize_case_sensitive_in_place(self):
        """
        Test standardize with case sensitive and no output
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta']
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                case_sensitive: true
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbrev'] == 'asap' and df.iloc[1]['Abbrev'] == 'eta'

    def test_standardize_case_sensitive_in_place_new_module(self):
        """
        Test standardize with case sensitive and no output
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta']
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: Abbrev
                case_sensitive: true
                model_id: 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['Abbrev'] == 'asap' and df.iloc[1]['Abbrev'] == 'eta'

    def test_standardize_case_sensitive_invalid_bool(self):
        """
        Test standardize with case sensitive with an invalid boolean
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta']
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: output
                case_sensitive: Huh?
                model_id: 6ca4ab44-8c66-40e8
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Non-boolean parameter in caseSensitive. Use True/False' in info.value.args[0]
        )

    def test_standardize_case_sensitive_invalid_bool_new_module(self):
        """
        Test standardize with case sensitive with an invalid boolean
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta']
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: Abbrev
                output: output
                case_sensitive: Huh?
                model_id: 6ca4ab44-8c66-40e8
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Non-boolean parameter in caseSensitive. Use True/False' in info.value.args[0]
        )

    def test_standardize_case_sensitive_multi_model(self):
        """
        Test standardize with case sensitive with multiple models
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta', 'IDK', 'OMW'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: output
                case_sensitive: true
                model_id: 
                - fc7d46e3-057f-47bd
                - 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == 'asap' and df.iloc[3]['output'] == 'OMW'

    def test_standardize_case_sensitive_multi_model_new_module(self):
        """
        Test standardize with case sensitive with multiple models
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta', 'IDK', 'OMW'],
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: Abbrev
                output: output
                case_sensitive: true
                model_id: 
                - fc7d46e3-057f-47bd
                - 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == 'asap' and df.iloc[3]['output'] == 'OMW'

    def test_standardize_case_insensitive_multi_model(self):
        """
        Test standardize with case insensitive with multiple models
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta', 'IDK', 'OMW'],
        })
        recipe = """
        wrangles:
            - standardize:
                input: Abbrev
                output: output
                case_sensitive: false
                model_id: 
                - fc7d46e3-057f-47bd
                - 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == 'As Soon As Possible' and df.iloc[3]['output'] == 'on my way'

    def test_standardize_case_insensitive_multi_model_new_module(self):
        """
        Test standardize with case insensitive with multiple models
        """
        data = pd.DataFrame({
        'Abbrev': ['asap', 'eta', 'IDK', 'OMW'],
        })
        recipe = """
        wrangles:
            - standardize.custom:
                input: Abbrev
                output: output
                case_sensitive: false
                model_id: 
                - fc7d46e3-057f-47bd
                - 6ca4ab44-8c66-40e8
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == 'As Soon As Possible' and df.iloc[3]['output'] == 'on my way'