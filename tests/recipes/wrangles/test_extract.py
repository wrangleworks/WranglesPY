import pytest
import wrangles
import pandas as pd

#
# Address
#
df_test_address = pd.DataFrame([['221 B Baker St., London, England, United Kingdom']], columns=['location'])

def test_address_street():
    recipe = """
    wrangles:
        - extract.address:
            input: location
            output: streets
            dataType: streets
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_address)
    assert df.iloc[0]['streets'] == ['221 B Baker St.']
    
def test_address_cities():
    recipe = """
    wrangles:
        - extract.address:
            input: location
            output: cities
            dataType: cities
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_address)
    assert df.iloc[0]['cities'] == ['London']
    
def test_address_countries():
    recipe = """
    wrangles:
            - extract.address:
                input: location
                output: country
                dataType: countries
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_address)
    assert df.iloc[0]['country'] == ['United Kingdom']
    
def test_address_regions():
    recipe = """
    wrangles:
        - extract.address:
            input: location
            output: regions
            dataType: regions
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_address)
    assert df.iloc[0]['regions'] == ['England']
    
# if the input is multiple columns (a list)
def test_address_5():
    data = pd.DataFrame({
        'col1': ['221 B Baker St., London, England, United Kingdom'],
        'col2': ['742 Evergreen St, Springfield, USA']
    })
    recipe = """
    wrangles:
      - extract.address:
          input:
            - col1
            - col2
          output:
            - out1
            - out2
          dataType: streets
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out2'][0] == '742 Evergreen St'

def test_address_where():
    """
    Test extract.address using where
    """
    data = pd.DataFrame({
        'address': ['221 B Baker St., London, England, United Kingdom', '742 Evergreen St, Springfield, USA'],
        'elevation': [1462, 2121]
    })
    recipe = """
    wrangles:
      - extract.address:
          input:
            - address
          output:
            - output
          dataType: streets
          where: elevation > 2000
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['output'] == "" and df.iloc[1]['output'][0] == '742 Evergreen St'
    
# if the input and output are not the same type
def test_address_multi_input():
    data = pd.DataFrame({
        'street': ['221 B Baker St.'],
        'city': ['London'],
        'region': ['England'],
        'country': ['United Kingdom']
    })
    recipe = """
    wrangles:
      - extract.address:
          input:
            - street
            - city
            - region
            - country
          output: out
          dataType: streets
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out'] == ['221 B Baker St.']

#
# Attributes
#

class TestExtractAttributes:
    """
    Extract Attributes testing
    """

    # Testing span
    df_test_attributes = pd.DataFrame([['hammer 5kg, 0.5m']], columns=['Tools'])

    def test_attributes_span(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: span
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes)
        assert df.iloc[0]['Attributes'] == {'length': ['0.5m'], 'weight': ['5kg']}

    # Testing Object
    def test_attributes_object(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: object
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes)
        assert df.iloc[0]['Attributes'] == {
            'length': [{'span': '0.5m', 'standard': '0.5 m', 'symbol': 'm', 'unit': 'metre', 'value': 0.5}],
            'weight': [{'span': '5kg', 'standard': '5 kg', 'symbol': 'kg', 'unit': 'kilogram', 'value': 5.0}]
            }

    df_test_attributes_all = pd.DataFrame([['hammer 13kg, 13m, 13deg, 13m^2, 13A something random 13hp 13N and 13W, 13psi random 13V 13m^3 stuff ']], columns=['Tools'])

    # Testing Angle
    def test_attributes_angle(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: span
                attribute_type: angle
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'][0] in ['13deg', '13°']

    # Testing area 
    def test_attributes_area(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: span
                attribute_type: area
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'][0] in ['13m^2', '13sq m']

    def test_attributes_area_standard(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: standard
                attribute_type: area
            """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13 sq m']

    # Testing Current
    def test_attributes_current(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: span
                attribute_type: current
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13A']

    def test_attributes_current_standard(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: standard
                attribute_type: current
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13 A']

    # Testing Force
    def test_attributes_force(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: span
                attribute_type: force
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13N']

    def test_attributes_force_standard(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: standard
                attribute_type: force
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13 N']

    # Testing Length
    def test_attributes_length(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: span
                attribute_type: length
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13m']

    def test_attributes_length_standard(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: standard
                attribute_type: length
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13 m']

    # Testing Power
    def test_attributes_power(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: span
                attribute_type: power
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13hp', '13W']

    def test_attributes_power_standard(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: standard
                attribute_type: power
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13 hp', '13 W']

    # Testing Pressure
    def test_attributes_pressure(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: span
                attribute_type: pressure
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13psi']

    def test_attributes_pressure_standard(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: standard
                attribute_type: pressure
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13 psi']

    # Testing electric potential
    def test_attributes_voltage_legacy(self):
        """
        Test voltage with new legacy name
        (electric potential)
        """
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: span
                attribute_type: electric potential
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13V']

    def test_attributes_voltage(self):
        """
        Test voltage with new name
        """
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: span
                attribute_type: voltage
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13V']

    def test_attributes_voltage_standard(self):
        """
        Test voltage with new name
        """
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: standard
                attribute_type: voltage
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13 V']

    # Testing volume
    def test_attributes_volume(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: span
                attribute_type: volume
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'][0] in ['13m^3', '13cu m']

    def test_attributes_volume_standard(self):
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: standard
                attribute_type: volume
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13 cu m']

    # Testing mass
    def test_attributes_mass_legacy(self):
        """
        Test with legacy name for weight (mass)
        """
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: span
                attribute_type: mass
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13kg']

    def test_attributes_weight(self):
        """
        Test with new name for weight
        """
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: span
                attribute_type: weight
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13kg']

    def test_attributes_mass_standard_weight(self):
        """
        Test with new name for weight
        """
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: standard
                attribute_type: weight
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13 kg']

    def test_attributes_mass_standard_mass(self):
        """
        Test with legacy name for weight (mass)
        """
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: standard
                attribute_type: mass
        """
        df = wrangles.recipe.run(recipe, dataframe=self.df_test_attributes_all)
        assert df.iloc[0]['Attributes'] == ['13 kg']

    # min/mid/max attributes
    def test_attributes_MinMidMax(self):
        data = pd.DataFrame({
            'Tools': ['object mass ranges from 13kg to 14.5kg to 18.2kg']
        })
        recipe = """
        wrangles:
            - extract.attributes:
                input: Tools
                output: Attributes
                responseContent: span
                attribute_type: mass
                bound: Minimum
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Invalid boundary setting. min, mid or max permitted.' in info.value.args[0]
        )
        
    # if the input is multiple columns (a list)
    def test_attributes_multi_col(self):
        data = pd.DataFrame({
            'col1': ['13 something 13kg 13 random'],
            'col2': ['3 something 3kg 3 random'],
        })
        recipe = """
        wrangles:
            - extract.attributes:
                input:
                - col1
                - col2
                output:
                - out1
                - out2
                responseContent: span
                attribute_type: mass
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out2'] == ['3kg']
        
    # if the input and output are not the same type
    def test_attributes_diff_type(self):
        data = pd.DataFrame({
            'col1': ['13 something 13kg 13 random'],
            'col2': ['3 something 3kg 3 random'],
        })
        recipe = """
        wrangles:
            - extract.attributes:
                input:
                - col1
                - col2
                output: out
                responseContent: span
                attribute_type: mass
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['out'] == ['13kg', '3kg']
        
    # if the input and output are different lengths
    def test_attributes_single_input_multi_output(self):
        data = pd.DataFrame({
            'col1': ['13 something 13kg 13 random'],
            'col2': ['3 something 3kg 3 random'],
        })
        recipe = """
        wrangles:
            - extract.attributes:
                input: col1
                output: 
                - out1
                - out2
                responseContent: span
                attribute_type: mass
        """
        with pytest.raises(ValueError) as info:
            raise wrangles.recipe.run(recipe, dataframe=data)
        assert (
            info.typename == 'ValueError' and
            'Extract must output to a single column or equal amount of columns as input.' in info.value.args[0]
        )

    def test_attributes_where(self):
        """
        Test extract.attributes using where
        """
        data = pd.DataFrame({
            'col1': ['13 something 13kg 13 random', '13mm wrench', '3/8in ratchet'],
            'numbers': [21, 3, 14]
        })
        recipe = """
        wrangles:
            - extract.attributes:
                input: col1
                output: output
                where: numbers < 10
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == "" and df.iloc[1]['output'] == {'length': ['13mm']}

    def test_attributes_sigFigs(self):
        """
        Test extract.attributes using where
        """
        data = pd.DataFrame({
            'col1': ['13 something 13.999999kg 13 random'],
        })
        recipe = """
        wrangles:
            - extract.attributes:
                input: col1
                output: output
                sigFigs: 2
                attribute_type: weight
                desired_unit: kilogram
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['output'][0] == ['14 kg']


class TestExtractAttributesAndConvert:
    """
    Extract attributes and convert them to a desired unit
    """

    def test_no_unit(self):
        """
        Test no unit to convert
        """
        data = pd.DataFrame(
            {'col': ['area 13 sqr yard', '26 sqr feet', '1300 square inches', '13 sqr meters']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: force
                desired_unit: newton
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [[], [], [], []]
        
    def test_no_unit_object(self):
        """
        Test no unit to convert object
        """
        data = pd.DataFrame(
            {'col': ['area 13 sqr yard', '26 sqr feet', '1300 square inches', '13 sqr meters']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: force
                desired_unit: newton
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [[], [], [], []]
        
        
    def test_non_existing_unit(self):
        """
        Test a desired unit that does not exists, should return error
        Adding lower to test on multiple systems
        """
        data = pd.DataFrame(
        {'col': ['1000 W', '1000 watts', '.01 MW', '1 kW', '1 hp']}
        )
        with pytest.raises(ValueError) as info:
            df = wrangles.recipe.run(
                recipe="""
                wrangles:
                - extract.attributes:
                    input: col
                    output: out
                    attribute_type: power
                    desired_unit: SuperMegaWatts
                """,
                dataframe=data
            )
        assert info.typename == 'ValueError' and info.value.args[0].lower() == 'extract.attributes - status code: 400 - bad request. {"valueerror":"invalid desiredunit provided"}\n \n'

    def test_wrong_match_1(self):
        """
        miss match of attribute type and unit
        """
        data = pd.DataFrame(
            {'col': ['100000 microFarad', '100000 µF', '10 kilograms', '10 ft']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: capacitance
                desired_unit: foot
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [[], [], [], []]
        
    def test_wrong_match_2(self):
        """
        miss match of attribute type and unit
        """
        data = pd.DataFrame(
            {'col': ['100000 microFarad', '100000 µF', '10 kilograms', '10 ft']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: length
                desired_unit: farad
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [[], [], [], []]
        
    def test_very_similar_units(self):
        """
        Testing volume and volumetric flow rate
        """
        data = pd.DataFrame(
            {'col': ['10 liter per minute', '10 liter', '20 liters per minute', '20 liters']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: volume
                desired_unit: gallons
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [[], ['2.64 gal'], [], ['5.28 gal']]
        

    #
    # area
    #

    def test_area_conversion_to_square_meters(self):
        """
        Test multiple units of area
        """
        data = pd.DataFrame(
            {'col': ['area 13 square yard', '26 square feet', '13 square meters']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: area
                desired_unit: square meters
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['10.9 sq m'], ['2.42 sq m'], ['13 sq m']]
        

    def test_area_conversion_square_meters_object(self):
        """
        Testing multiple units of area object
        """
        data = pd.DataFrame(
            {'col': ['area 13 square yard', '26 square feet', '13 square meters']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: area
                desired_unit: square meters
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][0] == [{'span': '13 square yard', 'standard': '10.9 sq m', 'symbol': 'sq m', 'unit': 'square metre', 'value': 10.9}]
        

    #
    # current
    #

    def test_current_conversion_current_object(self):
        """
        Test object of current
        """
        data = pd.DataFrame(
            {'col': ['something 1300 amps something']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: current
                desired_unit: kiloamps
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][0] == [{'span': '1300 amps', 'standard': '1.3 kA', 'symbol': 'kA', 'unit': 'kiloampere', 'value': 1.3}]
        

    def test_current_conversion_kiloamps_obj(self):
        """
        Test object of current
        """
        data = pd.DataFrame(
            {'col': ['something 1300 amps something']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: current
                desired_unit: kiloamps
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][0] == [{'span': '1300 amps', 'standard': '1.3 kA', 'symbol': 'kA', 'unit': 'kiloampere', 'value': 1.3}]
        
        
    #
    # force
    #

    def test_multile_force_kionewtons(self):
        """
        Test multiple units, one being close to force but not quite (pounds)
        """
        data = pd.DataFrame(
            {'col': ['something 1300 newtons something', 'something 1300 pounds something', 'something 1300 lbf']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: force
                desired_unit: kilonewtons
            """,
            dataframe=data
        )
        assert df['out'][1] == [] and df['out'][2] == ['5.78 kN'] and df['out'][0] == ['1.3 kN']
        
        
    def test_multile_forces_kilotons_obj(self):
        """
        Test multiple units, one being close to force but not quite (pounds) object
        """
        data = pd.DataFrame(
            {'col': ['something 1300 newtons something', 'something 1300 pounds something', 'something 1300 lbf']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: force
                desired_unit: kilonewtons
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][0] == [{'span': '1300 newtons', 'standard': '1.3 kN', 'symbol': 'kN', 'unit': 'kilonewton', 'value': 1.3}]

    #
    # power
    #

    def test_power_conversion_span(self):
        """
        Test multiple units of power
        """
        data = pd.DataFrame(
            {'col': ['1000 W', '1000 watts', '.01 MW', '1 kW', '1 hp']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: power
                desired_unit: kilowatts
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['1 kW'], ['1 kW'], ['10 kW'], ['1 kW'], ['0.746 kW']]
        
        
    def test_power_conversion_obj(self):
        """
        Test multiple units of power
        """
        data = pd.DataFrame(
            {'col': ['1000 W', '1000 watts', '.01 MW', '1 kW', '1 hp']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: power
                desired_unit: kilowatts
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][3] == [{'span': '1 kW', 'standard': '1 kW', 'symbol': 'kW', 'unit': 'kilowatt', 'value': 1.0}] 
        
        
    #
    # pressure
    #

    def test_pressure_conversion_span(self):
        """
        Test multiple units of pressure
        """
        data = pd.DataFrame(
            {'col': ['1000 Pa', '1000 pascals', '.01 MPa', '1 kPa', '1 bar', '1 psi', '1 torr']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: pressure
                desired_unit: kilopascals
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['1 kPa'], ['1 kPa'], ['10 kPa'], ['1 kPa'], ['100 kPa'], ['6.89 kPa'], ['0.133 kPa']]
        
    def test_pressure_conversion_obj(self):
        """
        Test multiple units of pressure
        """
        data = pd.DataFrame(
            {'col': ['1000 Pa', '1000 pascals', '.01 MPa', '1 kPa', '1 bar', '1 psi', '1 torr']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: pressure
                desired_unit: kilopascals
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][3] == [{'span': '1 kPa', 'standard': '1 kPa', 'symbol': 'kPa', 'unit': 'kilopascal', 'value': 1.0}]
        

    #
    # temperature
    #

    def test_temperature_conversion_span(self):
        """
        Test multiple units of temperature
        """
        data = pd.DataFrame(
            {'col': ['100 Kelvin', '100 rankine', '100 celsius', '100 °C', '100 °F', '100 fahrenheit']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: temperature
                desired_unit: celsius
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['-173 C'], ['-218 C'], ['100 C'], ['100 C'], ['37.8 C'], ['37.8 C']]
        

    def test_temperature_conversion_obj(self):
        """
        Test multiple units of temperature
        """
        data = pd.DataFrame(
            {'col': ['100 Kelvin', '100 rankine', '100 celsius', '100 °C', '100 °F', '100 fahrenheit']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: temperature
                desired_unit: celsius
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][3] == [{'span': '100 °C', 'standard': '100 C', 'symbol': 'C', 'unit': 'degree Celsius', 'value': 100}]


    #
    # volume
    #

    def test_volume_conversion_span(self):
        """
        Test multiple units of volume
        """
        data = pd.DataFrame(
            {'col': ['100 gallons', '1000 mL', '100 liters', '100 l', '100 gal', '100 liter']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: volume
                desired_unit: liters
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['379 l'], ['1 l'], ['100 l'], ['100 l'], ['379 l'], ['100 l']]
        
    def test_volume_conversion_obj(self):
        """
        Test multiple units of volume
        """
        data = pd.DataFrame(
            {'col': ['100 gallons', '1000 mL', '100 liters', '100 l', '100 gal', '100 liter']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: volume
                desired_unit: liters
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][2] == [{'span': '100 liters', 'standard': '100 l', 'symbol': 'l', 'unit': 'litre', 'value': 100}]
        
    #
    # volumetric flow rate
    #

    def test_volumetric_flow_rate_conversion_span(self):
        """
        Test multiple units of flow rate
        """
        data = pd.DataFrame(
            {'col': ['10 liter per minute', '10 gallon per minute', '10 cubic feet per minute', '10 liter per minute']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: volumetric flow
                desired_unit: gallon per minute
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['2.64 gpm'], ['10 gpm'], ['74.8 gpm'], ['2.64 gpm']]
        
    def test_volumetric_flow_rate_conversion_obj(self):
        """
        Test multiple units of flow rate object
        """
        data = pd.DataFrame(
            {'col': ['10 liter per minute', '10 gallon per minute', '10 cubic feet per minute', '10 liter per minute']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: volumetric flow
                desired_unit: gallon per minute
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][1] == [{'span': '10 gallon per minute', 'standard': '10 gpm', 'symbol': 'gpm', 'unit': 'gallon per minute', 'value': 10.0}]
        
        
        
    #
    # Length
    #

    def test_length_conversion_span(self):
        """
        Test multiple units of length
        """
        data = pd.DataFrame(
            {'col': ['1000 meters', '1000 m', '10000 cm', '1000 inches', '1000 yards', '1 mile', '1.5 km', '1000 ft']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: length
                desired_unit: miles
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['0.621 mi'], ['0.621 mi'], ['0.0621 mi'], ['0.0158 mi'], ['0.568 mi'], ['1 mi'], ['0.932 mi'], ['0.189 mi']]
        
    def test_length_conversion_obj(self):
        """
        Test multiple units of length
        """
        data = pd.DataFrame(
            {'col': ['1000 meters', '1000 m', '10000 cm', '1000 inches', '1000 yards', '1 mile', '1.5 km', '1000 ft']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: length
                desired_unit: miles
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][0] == [{'span': '1000 meters', 'standard': '0.621 mi', 'symbol': 'mi', 'unit': 'mile', 'value': 0.621}]
        
        
    #
    # weight
    #

    def test_weight_conversion_span(self):
        """
        Test multiple units of weight
        """
        data = pd.DataFrame(
            {'col': ['100 kg', '100 lbs', '100 lb', '100 pounds', '1000 g', '10000 grams', '100 kilograms', '100000 mg']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: weight
                desired_unit: pounds
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['220 lb'], ['100 lb'], ['100 lb'], ['100 lb'], ['2.2 lb'], ['22 lb'], ['220 lb'], ['0.22 lb']]
        
    def test_weight_conversion_obj(self):
        """
        Test multiple units of weight
        """
        data = pd.DataFrame(
            {'col': ['100 kg', '100 lbs', '100 lb', '100 pounds', '1000 g', '10000 grams', '100 kilograms', '100000 mg']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out 
                attribute_type: weight
                desired_unit: pounds
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][4] == [{'span': '1000 g', 'standard': '2.2 lb', 'symbol': 'lb', 'unit': 'pound-mass', 'value': 2.2}]
        
        
    def test_voltage_conversion_span(self):
        """
        Test multiple units of voltage
        """
        data = pd.DataFrame(
            {'col': ['1000 millivolts', '1000 mV', '1000 mV DC', '13 V AC']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: voltage
                desired_unit: volts
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['1 V'], ['1 V'], ['1 V'], ['13 V']]
        
    def test_voltage_conversion_obj(self):
        """
        Test multiple units of voltage
        """
        data = pd.DataFrame(
            {'col': ['1000 millivolts', '1000 mV', '1000 mV DC', '13 V AC']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out 
                attribute_type: voltage
                desired_unit: volts
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][2] == [{'span': '1000 mV', 'standard': '1 V', 'symbol': 'V', 'unit': 'volt', 'value': 1.0}]
        
    #
    # degree
    #

    def test_degree_conversion_span(self):
        """
        Test multiple units of degree
        """
        data = pd.DataFrame(
            {'col': ['1000 radian', '1000 radian']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: angle
                desired_unit: degrees
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['57300°'], ['57300°']]
        
    def test_degree_conversion_obj(self):
        """
        Test multiple units of degree- object
        """
        data = pd.DataFrame(
            {'col': ['1000 radian', '1000 radian']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: angle
                desired_unit: degrees
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][0] == [{'span': '1000 radian', 'standard': '57300°', 'symbol': '°', 'unit': 'degree angle', 'value': 57300}]
        
            

    #
    # Capacitance
    #

    def test_capacitance_conversion_span(self):
        """
        Test multiple units of capacitance
        """
        data = pd.DataFrame(
            {'col': ['100000 microFarad', '100000 µF', '10 Farad', '10 farad']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: capacitance
                desired_unit: farads
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['0.1 F'], ['0.1 F'], ['10 F'], ['10 F']]
        
    def test_capacitance_conversion_obj(self):
        """
        Test multiple units of capacitance
        """
        data = pd.DataFrame(
            {'col': ['100000 microFarad', '100000 µF', '10 Farad', '10 farad']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out 
                attribute_type: capacitance
                desired_unit: farads
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][0] == [{'span': '100000 microFarad', 'standard': '0.1 F', 'symbol': 'F', 'unit': 'farad', 'value': 0.1}]
        
        
    #
    # Frequency
    #


    def test_frequency_conversion__span(self):
        """
        Test multiple units of frequency
        """
        data = pd.DataFrame(
            {'col': ['1000 hertz', '1000 Hz', '100 kHz', '0.1 MHz']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: frequency
                desired_unit: kilohertz
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['1 kHz'], ['1 kHz'], ['100 kHz'], ['100 kHz']]
        
    def test_frequency_conversion_obj(self):
        """
        Test multiple units of frequency
        """
        data = pd.DataFrame(
            {'col': ['1000 hertz', '1000 Hz', '100 kHz', '0.1 MHz']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out 
                attribute_type: frequency
                desired_unit: kilohertz
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][3] == [{'span': '0.1 MHz', 'standard': '100 kHz', 'symbol': 'kHz', 'unit': 'kilohertz', 'value': 100}]


    #
    # Speed/Velocity
    #

    def test_speed_conversion_span(self):
        """
        Test multiple units of speed
        """
        data = pd.DataFrame(
            {'col': ['100 mph', '100 kph', '100 meters per second', '100 m/s', '100 feet per second', '100 ft/s']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: speed
                desired_unit: meters per second
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['44.7 mps'], ['27.8 mps'], ['100 mps'], ['100 mps'], ['30.5 mps'], ['30.5 mps']]
        
    def test_speed_conversion_obj(self):
        """
        Test multiple units of speed
        """
        data = pd.DataFrame(
            {'col': ['100 mph', '100 kph', '100 meters per second', '100 m/s', '100 feet per second', '100 ft/s']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out 
                attribute_type: speed
                desired_unit: meters per second
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][2] == [{'span': '100 meters per second', 'standard': '100 mps', 'symbol': 'mps', 'unit': 'metre per second', 'value': 100}]


    #
    # Charge
    #

    def test_charge_conversion_span(self):
        """
        Test multiple units of charge
        """
        data = pd.DataFrame(
            {'col': ['10 coulomb', '10000 mC']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: charge
                desired_unit: coulomb
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['10 C'], ['10 C']]
        
    def test_charge_conversion_obj(self):
        """
        Test multiple units of charge
        """
        data = pd.DataFrame(
            {'col': ['10 coulomb', '10000 mC']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out 
                attribute_type: charge
                desired_unit: coulomb
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][0] == [{'span': '10 coulomb', 'standard': '10 C', 'symbol': 'C', 'unit': 'coulomb', 'value': 10.0}]


    #
    # Data transfer rate
    #


    def test_data_transfer_rate_conversion_span(self):
        """
        Test multiple units of data transfer rate
        """
        data = pd.DataFrame(
            {'col': ['10000000 bps', '1000 kbps', '1 gbps']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: data transfer rate
                desired_unit: gigabit per second
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['0.01 Gbps'], ['0.001 Gbps'], ['1 Gbps']]
        
    def test_data_transfer_rate_conversion_obj(self):
        """
        Test multiple units of data transfer rate
        """
        data = pd.DataFrame(
            {'col': ['10000000 bps', '1000 kbps', '1 gbps']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out 
                attribute_type: data transfer rate
                desired_unit: gigabit per second
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][0] == [{'span': '10000000 bps', 'standard': '0.01 Gbps', 'symbol': 'Gbps', 'unit': 'gigabit per second', 'value': 0.01}]
        

    #
    # Electrical conductance
    #


    def test_electrical_conductance_conversion_span(self):
        """
        Test multiple units of electrical conductance. Be sure to update to have kilo and milli
        """
        data = pd.DataFrame(
            {'col': ['100 siemens']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: electrical conductance
                desired_unit: siemens
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['100 S']]
        
    def test_electrical_conductance_conversion_obj(self):
        """
        Test multiple units of electrical conductance. Be sure to update to have kilo and milli
        """
        data = pd.DataFrame(
            {'col': ['100 siemens']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out 
                attribute_type: electrical conductance
                desired_unit: siemens
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][0] == [{'span': '100 siemens', 'standard': '100 S', 'symbol': 'S', 'unit': 'siemens', 'value': 100}]
        
        
    #
    # Inductance
    #


    def test_inductance_conversion_span(self):
        """
        Test multiple units of inductance. Be sure to update to have kilo and milli
        """
        data = pd.DataFrame(
            {'col': ['1000 henry', '1000 H']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: inductance
                desired_unit: henry
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['1000 H'], ['1000 H']]
        
    def test_inductance_conversion_obj(self):
        """
        Test multiple units of inductance. Be sure to update to have kilo and milli
        """
        data = pd.DataFrame(
            {'col': ['1000 henry', '1000 H']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out 
                attribute_type: inductance
                desired_unit: henry
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][0] == [{'span': '1000 henry', 'standard': '1000 H', 'symbol': 'H', 'unit': 'henry', 'value': 1000}]


    #
    # intance frequency
    #


    def test_instance_frequency_conversion_span(self):
        """
        Test multiple units of frequency. Be sure to update to have kilo and milli
        """
        data = pd.DataFrame(
            {'col': ['1000 rpm', '1000 cps']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: instance frequency
                desired_unit: revolutions per minute
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['1000 rpm'], ['60000 rpm']]
        
    def test_instance_frequency_conversion_obj(self):
        """
        Test multiple units of frequency. Be sure to update to have kilo and milli
        """
        data = pd.DataFrame(
            {'col': ['1000 rpm', '1000 cps']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out 
                attribute_type: instance frequency
                desired_unit: revolutions per minute
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][0] == [{'span': '1000 rpm', 'standard': '1000 rpm', 'symbol': 'rpm', 'unit': 'revolutions per minute', 'value': 1000}]
        
        
        
    #
    # luminous intensity
    #


    def test_lumens_conversion_span(self):
        """
        Test multiple units of Lumens. Be sure to update to have kilo and milli
        """
        data = pd.DataFrame(
            {'col': ['1000 lumens', '1000 lm']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: luminous flux
                desired_unit: lumens
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['1000 lm'], ['1000 lm']]
        
    def test_lumens_conversion_obj(self):
        """
        Test multiple units of Lumens. Be sure to update to have kilo and milli
        """
        data = pd.DataFrame(
            {'col': ['1000 lumens', '1000 lm']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out 
                attribute_type: luminous flux
                desired_unit: lumens
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][0] == [{'span': '1000 lumens', 'standard': '1000 lm', 'symbol': 'lm', 'unit': 'lumen', 'value': 1000}]
        
        
    #
    # electrical resistance
    #

    def test_ohms_conversion_span(self):
        """
        Test multiple units of Lumens
        """
        data = pd.DataFrame(
            {'col': ['10 ohms', '10 Ω', '10000 milliohms', '10000 mΩ', '1 kΩ']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: electrical resistance
                desired_unit: ohms
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['10 Ω'], ['10 Ω'], ['10 Ω'], ['10 Ω'], ['1000 Ω']]
        
    def test_ohms_conversion_obj(self):
        """
        Test multiple units of Lumens
        """
        data = pd.DataFrame(
            {'col': ['10 ohms', '10 Ω', '10000 milliohms', '10000 mΩ', '1 kΩ']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col 
                output: out
                attribute_type: electrical resistance
                desired_unit: ohms
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][3] == [{'span': '10000 mΩ', 'standard': '10 Ω', 'symbol': 'Ω', 'unit': 'ohm', 'value': 10.0}]
        

    #
    # Energy
    #

    def test_energy_conversion_span(self):
        """
        Test multiple units of Lumens, be sure to add BTU and Calories are all kilocalories
        """
        data = pd.DataFrame(
            {'col': ['1000 joules', '1000 J', '10 kilojoules', '1 kwh']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: energy
                desired_unit: joules
            """,
            dataframe=data
        )
        assert df['out'].tolist() == [['1000 J'], ['1000 J'], ['10000 J'], ['3600000 J']]
        
    def test_energy_conversion_obj(self):
        """
        Test multiple units of Lumens, be sure to add BTU and Calories are all kilocalories
        """
        data = pd.DataFrame(
            {'col': ['1000 joules', '1000 J', '10 kilojoules', '1 kwh']}
        )
        df = wrangles.recipe.run(
            recipe="""
            wrangles:
            - extract.attributes:
                input: col
                output: out
                attribute_type: energy
                desired_unit: joules
                responseContent: object
            """,
            dataframe=data
        )
        assert df['out'][3] == [{'span': '1 kwh', 'standard': '3600000 J', 'symbol': 'J', 'unit': 'joule', 'value': 3600000}]
    
    
#
# Codes
#
def test_codes_inconsistent_input_output():
    """
    Check error if user provides inconsistent lists for input and output
    """
    data = pd.DataFrame({
        'col1': ['to gain access use Z1ON0101'],
        'col2': ['to gain access use Z1ON0101']
    })
    recipe = """
    wrangles:
      - extract.codes:
          input:
            - col1
            - col2
          output: 
            - code_a
            - code_b
            - code_c
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        'Extract must output to a single column or equal amount of columns as input.' in info.value.args[0]
    )

# Input is string
df_test_codes = pd.DataFrame([['to gain access use Z1ON0101']], columns=['secret'])

def test_extract_codes_2():
    recipe = """
    wrangles:
      - extract.codes:
          input: secret
          output: code
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_codes)
    assert df.iloc[0]['code'] == ['Z1ON0101']
    
# column is a list
df_test_codes_list = pd.DataFrame([[['to', 'gain', 'access', 'use', 'Z1ON0101']]], columns=['secret'])

def test_extract_codes_list():
    recipe = """
    wrangles:
      - extract.codes:
          input: secret
          output: code
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_codes_list)
    assert df.iloc[0]['code'] == ['Z1ON0101']
    

# Multiple columns as inputs
df_test_codes_multi_input = pd.DataFrame(
  {
    'code1': ['code Z1ON0101-1'],
    'code2': ['code Z1ON0101-2']
  }
)

def test_extract_codes_milti_input():
    recipe = """
    wrangles:
      - extract.codes:
          input: 
            - code1
            - code2
          output: Codes
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_codes_multi_input)
    assert df.iloc[0]['Codes'] == ['Z1ON0101-1', 'Z1ON0101-2']

# Multiple outputs and Inputs
def test_extract_codes_milti_input_output():
    recipe = """
    wrangles:
      - extract.codes:
          input: 
            - code1
            - code2
          output:
            - out1
            - out2
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_codes_multi_input)
    assert df.iloc[0]['out2'] == ['Z1ON0101-2']

def test_extract_codes_one_input_multi_output():
    recipe = """
    wrangles:
      - extract.codes:
          input: 
            - code1
          output:
            - out1
            - out2
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=df_test_codes_multi_input)
    assert (
        info.typename == 'ValueError' and
        'Extract must output to a single column or equal amount of columns as input.' in info.value.args[0]
    )

#
# Custom Extraction
#

# Input is String
df_test_custom = pd.DataFrame([['My favorite pokemon is charizard!']], columns=['Fact'])

def test_extract_custom_1():
    recipe = """
    wrangles:
      - extract.custom:
          input: Fact
          output: Fact Output
          model_id: 1eddb7e8-1b2b-4a52
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_custom)
    assert df.iloc[0]['Fact Output'] == ['Charizard']

# Input is String
df_test_custom = pd.DataFrame([['My favorite pokemon is charizard!']], columns=['Fact'])

def test_custom_one_output():
    """
    Test using extract.custom with a single output
    """
    data = pd.DataFrame({
        'col1': ['My favorite pokemon is charizard!'],
        'col2': ['My favorite pokemon is charizard2!']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input:
            - col1
            - col2
          output:
            - Fact Out
          model_id: 1eddb7e8-1b2b-4a52
    """
    df =  wrangles.recipe.run(recipe, dataframe=data)
    assert df['Fact Out'][0] == ['Charizard']

# Incorrect model_id missing "${ }" around value
def test_extract_custom_3():
    data = pd.DataFrame({
        'col1': ['My favorite pokemon is charizard!'],
        'col2': ['My favorite pokemon is charizard2!']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input:
            - col1
            - col2
          output:
            - Fact Out
            - Fact Out 2
          model_id: noWork
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        'Incorrect or missing values in model_id. Check format is XXXXXXXX-XXXX-XXXX' in info.value.args[0]
    )

def test_extract_custom_labels():
    """
    Test use_labels option to group output
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - extract.custom:
              input: col1
              output: col2
              model_id: 829c1a73-1bfd-4ac0
              use_labels: true
        """,
        dataframe = pd.DataFrame({
            'col1': ['small blue cotton jacket']
        })
    )
    assert (
        df['col2'][0]['colour'] == ['blue'] and
        df['col2'][0]['size'] == ['small']
    )

# Extract Regex Extract
def test_extract_regex():
    data = pd.DataFrame({
        'col': ['Random Pikachu Random', 'Random', 'Random Random Pikachu']
    })
    recipe = """
    wrangles:
      - extract.regex:
          input: col
          output: col_out
          find: Pikachu
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['col_out'] == ['Pikachu']
    
def test_extract_regex_where():
    """
    Test extract.regex with where
    """
    data = pd.DataFrame({
        'col1': ['Pikachu', 'Stuff', 'Pikachu and Charizard'],
        'numbers': [23, 54, 75]
    })
    recipe = r"""
    wrangles:
      - extract.regex:
          input: col1
          output: col_out
          find: P\w+u
          where: numbers > 50
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['col_out'] == "" and df.iloc[1]['col_out'] == [] and df.iloc[2]['col_out'][0] == 'Pikachu'
    
# incorrect model_id - forget to use ${}
def test_extract_custom_6():
    data = pd.DataFrame({
        'col': ['Random Pikachu Random', 'Random', 'Random Random Pikachu']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: col_out
          model_id: {model_id_here}
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        'Incorrect model_id type.\nIf using Recipe, may be missing "${ }" around value' in info.value.args[0]
    )

def test_extract_with_standardize_model_id():
    data = pd.DataFrame({
        'col': ['Random Pikachu Random', 'Random', 'Random Random Pikachu']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: col_out
          model_id: 6ca4ab44-8c66-40e8
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        'Using standardize model_id 6ca4ab44-8c66-40e8 in an extract function.' in info.value.args[0]
    )

# Input column is list
df_test_custom_list = pd.DataFrame([[['Charizard', 'Cat', 'Pikachu', 'Mew', 'Dog']]], columns=['Fact'])

def test_extract_custom_list():
    recipe = """
    wrangles:
      - extract.custom:
          input: Fact
          output: Fact Output
          model_id: 1eddb7e8-1b2b-4a52
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_custom_list)
    assert df.iloc[0]['Fact Output'][0] in ['Pikachu', 'Mew', 'Charizard']

# Testing Multi column input
df_test_custom_multi_input = pd.DataFrame(
  {
    'col1': ['First Place Pikachu'],
    'col2': ['Second Place Charizard']
  }
)

def test_extract_custom_empty_input():
    """
    Test custom extract with an empty input
    e.g. in the case a where filters all rows
    """
    df = wrangles.recipe.run(
        """
        wrangles:
        - extract.custom:
            input:
                - col1
                - col2
            output: col3
            model_id: 1eddb7e8-1b2b-4a52
        """,
        dataframe=pd.DataFrame({
            'col1': [],
            'col2': []
        })
    )
    assert (
        list(df.columns) == ['col1', 'col2', 'col3'] and
        len(df) == 0
    )

def test_extract_custom_multi_input():
    recipe = """
    wrangles:
      - extract.custom:
          input:
            - col1
            - col2
          output: Fact Output
          model_id: 1eddb7e8-1b2b-4a52
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_custom_multi_input)
    assert (
        'Charizard' in df['Fact Output'][0] and
        'Pikachu' in df['Fact Output'][0]
    )

# Multiple output and inputs
def test_extract_custom_mulit_input_output():
    recipe = """
    wrangles:
      - extract.custom:
          input:
            - col1
            - col2
          output:
            - Fact1
            - Fact2
          model_id: 1eddb7e8-1b2b-4a52
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_custom_multi_input)
    assert df.iloc[0]['Fact2'] == ['Charizard']
    
def test_extract_custom_where():
    """
    Test custom extract with where
    """
    data = pd.DataFrame({
        'col1': ['Pikachu', 'Stuff', 'Pikachu and Charizard'],
        'col2': ['Charizard', 'More stuff', 'Pikachu and Charizard']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input:
            - col1
          output:
            - output col
          model_id: 1eddb7e8-1b2b-4a52
          where: col1 LIKE col2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['output col'] == "" and df.iloc[2]['output col'] == ['Charizard', 'Pikachu']

def test_extract_custom_multi_io_where():
    """
    Test custom extract with multiple inputs and outputs using where
    """
    data = pd.DataFrame({
        'col1': ['Pikachu', 'Stuff', 'Pikachu and Charizard'],
        'col2': ['Charizard', 'More stuff', 'Pikachu and Charizard']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input:
            - col1
            - col2
          output:
            - output col1
            - output col2
          model_id: 1eddb7e8-1b2b-4a52
          where: col1 LIKE col2
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['output col1'] == "" and df.iloc[2]['output col2'] == ['Charizard', 'Pikachu']

# multiple different custom extract at the same time
def test_extract_multi_custom():
    data = pd.DataFrame({
        'Pokemon': ['my favorite pokemon is Charizard'],
        'AI':['My favorite AIs are Dolores and TARS both from are great']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input:
            - Pokemon
            - AI
          output:
            - Fact1
            - Fact2
          model_id:
            - 1eddb7e8-1b2b-4a52
            - 05f6bb73-de04-4cb6
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Fact2'][0] in ['Dolores', 'TARS']

def test_extract_custom_first_only():
    """
    Test that the first only parameter works correctly. use_labels is False
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: Pikachu vs Charizard

        wrangles:
          - extract.custom:
              input: header
              output: results
              model_id: 1eddb7e8-1b2b-4a52
              use_labels: false
              first_element: True
        """
    )
    assert df['results'][0] == 'Charizard'

def test_extract_custom_case_sensitive():
    """
    Test extract.custom with case sensitivity
    """
    data = pd.DataFrame({
        'col1': ['Charizard'],
        'col2': ['not charizard']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: 
            - col1
            - col2
          output: Output
          case_sensitive: true
          model_id: 1eddb7e8-1b2b-4a52
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Output'] == ['Charizard']

def test_extract_custom_case_insensitive():
    """
    Test extract.custom with case insensitivity
    """
    data = pd.DataFrame({
        'col1': ['Charizard'],
        'col2': ['not jynx']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: 
            - col1
            - col2
          output: Output
          case_sensitive: false
          model_id: 1eddb7e8-1b2b-4a52
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Output'] == ['Charizard', 'Jynx']

def test_extract_custom_case_default():
    """
    Test extract.custom with case sensitivity's default
    """
    data = pd.DataFrame({
        'col1': ['Charizard'],
        'col2': ['not jynx']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: 
            - col1
            - col2
          output: Output
          model_id: 1eddb7e8-1b2b-4a52
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Output'] == ['Charizard', 'Jynx']

def test_extract_custom_case_invalid_bool():
    """
    Test extract.custom with case sensitivity given an invalid bool
    """
    data = pd.DataFrame({
        'col1': ['Charizard'],
        'col2': ['not jynx']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: 
            - col1
            - col2
          output: Output
          case_sensitive: You Tell Me
          model_id: 1eddb7e8-1b2b-4a52
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        '{"Error":"Non-boolean parameter in caseSensitive. Use True/False"}' in info.value.args[0]
    )

def test_extract_custom_case_sensitive_in_place():
    """
    Test extract.custom with case sensitivity and no output
    """
    data = pd.DataFrame({
        'col1': ['Charizard'],
        'col2': ['not charizard']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: 
            - col1
            - col2 
          case_sensitive: true
          model_id: 1eddb7e8-1b2b-4a52
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['col1'] == ['Charizard'] and df.iloc[0]['col2'] == []

def test_extract_custom_case_sensitive_multi_model():
    """
    Test extract.custom with case sensitivity using multiple models
    """
    data = pd.DataFrame({
        'col1': ['Charizard', 'not charizard', 'not agent smith'],
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col1 
          output: output
          case_sensitive: true
          model_id: 
            - 1eddb7e8-1b2b-4a52
            - 05f6bb73-de04-4cb6
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['output'] == ['Charizard'] and df.iloc[2]['output'] == []

def test_extract_custom_raw():
    """
    Test extract.custom using extract_raw
    """
    data = pd.DataFrame({
        'col1': ['The first one is blue small', 'Second is green size medium', 'Third is black and the size is small'],
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col1 
          output: output
          extract_raw: True
          model_id: 829c1a73-1bfd-4ac0
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['output'] == ['blue', 'small'] and df.iloc[2]['output'] == ['black', 'small']

def test_extract_custom_raw_first_element():
    """
    Test extract.custom using extract_raw and first_element
    """
    data = pd.DataFrame({
        'col1': ['The first one is blue small', 'Second is green size medium', 'Third is black and the size is small'],
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col1 
          output: output
          extract_raw: True
          first_element: True
          model_id: 829c1a73-1bfd-4ac0
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['output'] == 'blue' and df.iloc[2]['output'] == 'black' 

def test_extract_custom_raw_case_sensitive():
    """
    Test extract.custom using extract_raw and case sensitive
    """
    data = pd.DataFrame({
        'col1': ['The first one is Blue small', 'Second is green size medium', 'Third is black and the size is Small'],
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col1 
          output: output
          extract_raw: True
          case_sensitive: True
          model_id: 829c1a73-1bfd-4ac0
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['output'] == ['small'] and df.iloc[2]['output'] == ['black'] 

def test_extract_custom_use_spellcheck():
    """
    Test extract.custom with use_spellcheck
    """
    data = pd.DataFrame({
        'col1': ['The first one is smal', 'Second is size medum', 'Third is coton'],
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col1 
          output: output
          use_spellcheck: True
          model_id: 829c1a73-1bfd-4ac0
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['output'] == ['size: small'] and df.iloc[2]['output'] == ['cotton'] 

def test_extract_custom_use_spellcheck_extract_raw():
    """
    Test extract.custom with use_spellcheck and extract_raw
    """
    data = pd.DataFrame({
        'col1': ['The first one is smal', 'Second is size medum', 'Third is coton'],
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col1 
          output: output
          use_spellcheck: True
          extract_raw: True
          model_id: 829c1a73-1bfd-4ac0
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['output'] == ['small'] and df.iloc[1]['output'] == ['medium'] 

def test_extract_custom_ai_single_output():
    """
    Test extract.custom with AI that produces
    only a single column output
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: example 1 2 3 4 5
        wrangles:
          - extract.custom:
              input: header
              output: results
              model_id: 8e4ce4c6-9908-4f67
        """
    )
    assert df["results"][0] == '["1", "2", "3", "4", "5"]'

def test_extract_custom_ai_multiple_output():
    """
    Test extract.custom with AI that produces
    a multi column output
    """
    df = wrangles.recipe.run(
        """
        read:
          - test:
              rows: 1
              values:
                header: example 1 2 3 4 5 word
        wrangles:
          - extract.custom:
              input: header
              output: results
              model_id: 1f3ba62b-ce20-486e
        """
    )
    assert (
        "Words" in df["results"][0] and
        "Numbers" in df["results"][0]
    )

# combinations of use_labels and first_element begins
def test_use_labels_true_and_first_element_true():
    """
    Use_labels and first_element set to true. output is a dictionary with only one value (string)    
    """
    data = pd.DataFrame({
        'col': ['colour: blue size: small colour: green']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: out
          model_id: 829c1a73-1bfd-4ac0
          use_labels: true
          first_element: true
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['out'][0] == {'colour': 'blue', 'size': 'small'} or {'colour': 'green', 'size': 'small'}
    
def test_use_labels_false_first_element_true():
    """
    Use labels is false and first element is true. output is a string only
    """
    data = pd.DataFrame({
        'col': ['colour: blue size: small colour: green size: large']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: out
          model_id: 829c1a73-1bfd-4ac0
          use_labels: false
          first_element: true
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['out'][0] == 'size: small' or df['out'][0] == 'colour: green' or df['out'][0] == 'colour: blue'

def test_use_labels_multiple():
    """
    Use labels true and first element is false. output is a dictionary where values are lists
    Testing use labels with multiple same labels and other labels
    """
    data = pd.DataFrame({
        'col': ['colour: blue size: small colour: black']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: out
          model_id: 829c1a73-1bfd-4ac0
          use_labels: true
          first_element: false
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df['out'][0] == {'size': ['small'], 'colour': ['blue', 'black']} or df['out'][0] == {'colour': ['black', 'blue'], 'size': ['small']}
    
def test_use_labels_same_key():
    """
    Testing use labels where multiple labels that are the same only. 
    This should put all of the values from the same labels in a list
    """
    data = pd.DataFrame({
        'col': ['colour: blue colour: green colour: black']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: out
          model_id: 829c1a73-1bfd-4ac0
          use_labels: true
          first_element: false
    """
    df =  wrangles.recipe.run(recipe, dataframe=data)
    df['out'][0]['colour'] == ['green', 'blue', 'black']
    
def test_unlabeled_in_use_labels():
    """
    Testing unlabeled key. This everything that is not specified in the labels
    """
    data = pd.DataFrame({
        'col': ['colour: blue colour: green colour: black red']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: out
          model_id: 829c1a73-1bfd-4ac0
          use_labels: true
          first_element: false
    """
    df =  wrangles.recipe.run(recipe, dataframe=data)
    df['out'][0] == {'colour': ['green', 'blue', 'black'], 'Unlabeled': ['red']}
    
def test_unlabeled_only():
    """
    Getting unlabeled only
    """
    data = pd.DataFrame({
        'col': ['my color is red']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: out
          model_id: 829c1a73-1bfd-4ac0
          use_labels: true
          first_element: false
    """
    df =  wrangles.recipe.run(recipe, dataframe=data)
    assert df['out'][0] == {'Unlabeled': ['red']}
    
def test_unlabeled_only_with_first_element_true():
    """
    Unlabeled only with first_element set to true
    """
    data = pd.DataFrame({
        'col': ['my color is red']
    })
    recipe = """
    wrangles:
      - extract.custom:
          input: col
          output: out
          model_id: 829c1a73-1bfd-4ac0
          use_labels: true
          first_element: true
    """
    df =  wrangles.recipe.run(recipe, dataframe=data)
    assert df['out'][0] == {'Unlabeled': 'red'}
    
#
# Properties
#
df_test_properties = pd.DataFrame([['OSHA approved Red White Blue Round Titanium Shield']], columns=['Tool'])

def test_extract_colours():
    recipe = """
    wrangles:
    - extract.properties:
        input: Tool
        output: prop
        property_type: colours
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_properties)
    check_list = ['Blue', 'Red', 'White']
    assert df.iloc[0]['prop'][0] in check_list and df.iloc[0]['prop'][1] in check_list and df.iloc[0]['prop'][2] in check_list
    
def test_extract_materials():
    recipe = """
    wrangles:
    - extract.properties:
        input: Tool
        output: prop
        property_type: materials
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_properties)
    assert df.iloc[0]['prop'] == ['Titanium']
    
def test_extract_shapes():
    recipe = """
    wrangles:
    - extract.properties:
        input: Tool
        output: prop
        property_type: shapes
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_properties)
    assert df.iloc[0]['prop'] == ['Round']
    
def test_extract_standards():
    recipe = """
    wrangles:
    - extract.properties:
        input: Tool
        output: prop
        property_type: standards
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_properties)
    assert df.iloc[0]['prop'] == ['OSHA']
    
# if the input is multiple columns (a list)
def test_properties_5():
    data = pd.DataFrame({
        'col1': ['Why is the sky blue?'],
        'col2': ['Temperature of a star if it looks blue'],
    })
    recipe = """
    wrangles:
      - extract.properties:
          input:
            - col1
            - col2
          output:
            - out1
            - out2
          property_type: colours
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out2'] == ['Blue']
    
# if the input and output are not the same type
def test_properties_6():
    data = pd.DataFrame({
        'col1': ['Why is the sky blue?'],
        'col2': ['Temperature of a star if it looks blue'],
    })
    recipe = """
    wrangles:
      - extract.properties:
          input:
            - col1
            - col2
          output: out
          property_type: colours
    """

    df = wrangles.recipe.run(recipe, dataframe=data)
    assert 'Blue' in df.iloc[0]['out'] and 'Sky Blue' in df.iloc[0]['out']
    
#
# HTML
#

# text
df_test_html = pd.DataFrame([r'<a href="https://www.wrangleworks.com/">Wrangle Works!</a>'], columns=['HTML'])

def test_extract_html_text():
    recipe = """
    wrangles:
      - extract.html:
          input: HTML
          output: 
            - Text
          data_type: text
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_html)
    assert df.iloc[0]['Text'] == 'Wrangle Works!'
    
# Links
def test_extract_html_links():
    recipe = """
    wrangles:
      - extract.html:
          input: HTML
          output: 
            - Links
          data_type: links
    """
    df = wrangles.recipe.run(recipe, dataframe=df_test_html)
    assert df.iloc[0]['Links'] == ['https://www.wrangleworks.com/']
    
#
# Brackets
#

class TestExtractBrackets:
    """
    All tests for extract.brackets
    """

    def test_extract_brackets_1(self):
        data = pd.DataFrame({
            'col': ['[1234]', '{1234}']
        })
        recipe = """
        wrangles:
        - extract.brackets:
            input: col
            output: no_brackets
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['no_brackets'] == '1234'
        
    # if the input is multi column (a list)
    def test_extract_brackets_2(self):
        data = pd.DataFrame({
            'col': ['[1234]'],
            'col2': ['{1234}'],
        })
        recipe = """
        wrangles:
        - extract.brackets:
            input:
                - col
                - col2
            output:
                - no_brackets
                - no_brackets2
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['no_brackets2'] == '1234'
        
    # if the input and output are not the same type
    def test_extract_brackets_3(self):
        data = pd.DataFrame({
            'col': ['[12345]'],
            'col2': ['{1234}'],
        })
        recipe = """
        wrangles:
        - extract.brackets:
            input:
                - col
                - col2
            output: output
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == '12345, 1234'

    # if the input and output are not the same type
    def test_extract_brackets_multi_input(self):
        data = pd.DataFrame({
            'col': ['[12345]'],
            'col2': ['[6789]'],
        })
        recipe = """
        wrangles:
        - extract.brackets:
            input:
                - col
                - col2
            output: output
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == '12345, 6789'

    def test_extract_brackets_multi_input_where(self):
        """
        Test extract.brackets with multiple inputs, and one output using where
        """
        data = pd.DataFrame({
            'col': ['[12345]', '[this is in brackets]', '[more stuff in brackets]'],
            'col2': ['[6789]', 'This is not in brackets', '[But this is]'],
            'numbers': [4, 6, 10]
        })
        recipe = """
        wrangles:
        - extract.brackets:
            input:
                - col
                - col2
            output: output
            where: numbers > 4
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == "" and df.iloc[1]['output'] == 'this is in brackets' and df.iloc[2]['output'] == 'more stuff in brackets, But this is'


    def test_brackets_round(self):
        data = pd.DataFrame({
            'input': ['(some)', 'example']
        })
        recipe = """
        wrangles:
            - extract.brackets:
                input: input
                output: output
                find: round
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == 'some'
        assert df.iloc[1]['output'] == ''

    def test_brackets_square(self):
        data = pd.DataFrame({
            'input': ['[example]', 'example']
        })
        recipe = """
        wrangles:
            - extract.brackets:
                input: input
                output: output
                find: square
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == 'example'
        assert df.iloc[1]['output'] == ''

    def test_brackets_round_square(self):
        data = pd.DataFrame({
            'input': ['(some)', '[example]']
        })
        recipe = """
        wrangles:
            - extract.brackets:
                input: input
                output: output
                find: 
                    - round
                    - square
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == 'some'
        assert df.iloc[1]['output'] == 'example'

    def test_all_brackets(self):
        data = pd.DataFrame({
            'input': ['(some)', '[example]', '{example}', '<example>']
        })
        recipe = """
        wrangles:
            - extract.brackets:
                input: input
                output: output
                find: 
                    - round
                    - square
                    - curly
                    - angled
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['output'].tolist() == ['some', 'example', 'example', 'example']

    def test_all_brackets_no_find(self):
        data = pd.DataFrame({
            'input': ['(some) and (some2)', '[example]', '{example}', '<example>']
        })
        recipe = """
        wrangles:
            - extract.brackets:
                input: input
                output: output
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['output'].tolist() == ['some, some2', 'example', 'example', 'example']

    def test_all_brackets_with_all_specified(self):
        data = pd.DataFrame({
            'input': ['(some)', '[example]', '{example}', '<example>']
        })
        recipe = """
        wrangles:
            - extract.brackets:
                input: input
                output: output
                find: all
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['output'].tolist() == ['some', 'example', 'example', 'example']

    def test_multi_bracket_all_included(self):
        data = pd.DataFrame({
            'input': ['(some)', '[example]', '{example}', '<example>']
        })
        recipe = """
        wrangles:
            - extract.brackets:
                input: input
                output: output
                find: 
                    - round
                    - square
                    - all
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['output'].tolist() == ['some', 'example', '', '']

    def test_all_brackets_no_find_raw(self):
        data = pd.DataFrame({
            'input': ['(some) and (some2)', '[example]', '{example}', '<example>']
        })
        recipe = """
        wrangles:
            - extract.brackets:
                input: input
                output: output
                include_brackets: true
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['output'].tolist() == ['(some), (some2)', '[example]', '{example}', '<example>']

    def test_all_brackets_raw(self):
        data = pd.DataFrame({
            'input': ['(some)', '[example]', '{example}', '<example>']
        })
        recipe = """
        wrangles:
            - extract.brackets:
                input: input
                output: output
                find: 
                    - round
                    - square
                    - curly
                    - angled
                include_brackets: true
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['output'].tolist() == ['(some)', '[example]', '{example}', '<example>']

    def test_two_bracket_types(self):
        data = pd.DataFrame({
            'input': ['(some)', '[example]', '{example}', '<example>']
        })
        recipe = """
        wrangles:
            - extract.brackets:
                input: input
                output: output
                find: 
                    - round
                    - square
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df['output'].tolist() == ['some', 'example', '', '']

    def test_brackets_curly(self):
        data = pd.DataFrame({
            'input': ['{example}', 'example']
        })
        recipe = """
        wrangles:
            - extract.brackets:
                input: input
                output: output
                find: curly
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == 'example'
        assert df.iloc[1]['output'] == ''

    def test_brackets_angled(self):
        data = pd.DataFrame({
            'input': ['<example>', 'example']
        })
        recipe = """
        wrangles:
            - extract.brackets:
                input: input
                output: output
                find: angled
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == 'example'
        assert df.iloc[1]['output'] == ''

    def test_brackets_extract_raw(self):
        data = pd.DataFrame({
            'input': ['(some)', '[example]']
        })
        recipe = """
        wrangles:
            - extract.brackets:
                input: input
                output: output
                include_brackets: true
        """
        df = wrangles.recipe.run(recipe, dataframe=data)
        assert df.iloc[0]['output'] == '(some)'
        assert df.iloc[1]['output'] == '[example]'


#
# Date Properties
#

# Basic function
def test_date_properties_1():
    data = pd.DataFrame({
        'col1': ['12/24/2000'],
    })
    recipe = """
    wrangles:
      - extract.date_properties:
          input: col1
          output: out1
          property: quarter
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'] == 4
    
# not valid property types
def test_date_properties_2():
    data = pd.DataFrame({
        'col1': ['12/24/2000'],
    })
    recipe = """
    wrangles:
      - extract.date_properties:
          input: col1
          output: out1
          property: millennium
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        '"millennium" not a valid date property.' in info.value.args[0]
    )

# Multiple inputs to single output
def test_date_properties_multi_input():
    data = pd.DataFrame({
        'col1': ['12/24/2000'],
        'col2': ['4/24/2023']
    })
    recipe = """
    wrangles:
      - extract.date_properties:
          input: 
            - col1
            - col2
          output: out1
          property: week_day_name
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'] == ['Sunday','Monday']

# Multiple inputs and outputs
def test_date_properties_multi_input_multi_output():
    data = pd.DataFrame({
        'col1': ['12/24/2000'],
        'col2': ['4/24/2023']
    })
    recipe = """
    wrangles:
      - extract.date_properties:
          input: 
            - col1
            - col2
          output: 
            - out1
            - out2
          property: week_day_name
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['out1'] == 'Sunday' and df.iloc[0]['out2'] == 'Monday'

def test_date_properties_multi_input_multi_output_where():
    """
    Test extract.date_properties with multiple i/o's using where
    """
    data = pd.DataFrame({
        'col1': ['12/24/2000', '11/10/1987', '3/13/2023'],
        'col2': ['4/24/2023', '1/9/2006', '7/17/1907'],
        'number': [4, 9, 3]
    })
    recipe = """
    wrangles:
      - extract.date_properties:
          input: 
            - col1
            - col2
          output: 
            - out1
            - out2
          property: week_day_name
          where: number > 3
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[1]['out1'] == 'Tuesday' and df.iloc[2]['out2'] == ""
    
#
# Date range
#

# basic function
def test_date_range_1():
    data = pd.DataFrame({
      'date1': ['08-13-1992'],
      'date2': ['08-13-2022'],
    })
    recipe = """
    wrangles:
      - extract.date_range:
          start_time: date1
          end_time: date2
          output: Range
          range: years
    """
    df = wrangles.recipe.run(recipe, dataframe=data)
    assert df.iloc[0]['Range'] == 29
    
    
# invalid range
def test_date_range_2():
    data = pd.DataFrame({
      'date1': ['08-13-1992'],
      'date2': ['08-13-2022'],
    })
    recipe = """
    wrangles:
      - extract.date_range:
          start_time: date1
          end_time: date2
          output: Range
          range: millennium
    """
    with pytest.raises(ValueError) as info:
        raise wrangles.recipe.run(recipe, dataframe=data)
    assert (
        info.typename == 'ValueError' and
        '"millennium" not a valid frequency' in info.value.args[0]
    )

def test_ai():
    """
    Test openai extract with a single input and output
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - extract.ai:
              model: gpt-4o
              api_key: ${OPENAI_API_KEY}
              seed: 1
              timeout: 60
              retries: 2
              output:
                length:
                  type: string
                  description: >-
                    Any lengths found in the data
                    such as cm, m, ft, etc.
        """,
        dataframe=pd.DataFrame({
            "data": [
                "wrench 25mm",
                "6m cable",
                "screwdriver 3mm"
            ],
        })
    )
    # This is temperamental
    # Score as 2/3 as good enough for test to pass
    matches = sum([
        df['length'][0] == '25mm',
        df['length'][1] == '6m',
        df['length'][2] == '3mm'
    ])
    assert matches >= 2

def test_ai_multiple_output():
    """
    Test AI extract with multiple outputs
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - extract.ai:
              model: gpt-4o
              api_key: ${OPENAI_API_KEY}
              seed: 1
              timeout: 60
              retries: 2
              output:
                length:
                  type: string
                  description: >-
                    Any lengths found in the data
                    such as cm, m, ft, etc.
                type:
                  type: string
                  description: >-
                    The type of item in the data
                    such as spanner, cellphone, etc.
        """,
        dataframe=pd.DataFrame({
            "data": [
                "wrench 25mm",
                "6m cable",
                "screwdriver 3mm"
            ],
        })
    )
    # This is temperamental
    # Score as 4/6 as good enough for test to pass
    matches = sum([
        df['length'][0] == '25mm',
        df['length'][1] == '6m',
        df['length'][2] == '3mm',
        df['type'][0] == 'wrench',
        df['type'][1] == 'cable',
        df['type'][2] == 'screwdriver'
    ])
    assert matches >= 4

def test_ai_multiple_input():
    """
    Test AI extract with multiple inputs
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - extract.ai:
              model: gpt-4o
              api_key: ${OPENAI_API_KEY}
              seed: 1
              timeout: 60
              retries: 2
              output:
                text:
                  type: string
                  description: >-
                    Concatenate the type and
                    length to form a single output text
                    e.g. bolt 5mm
        """,
        dataframe=pd.DataFrame({
            "type": [
                "wrench",
                "cable",
                "screwdriver"
            ],
            "length": [
                "25mm",
                "6m",
                "3mm"
            ]
        })
    )
    # This is temperamental
    # Score as 2/3 as good enough for test to pass
    matches = sum([
        df['text'][0] == 'wrench 25mm',
        df['text'][1] == 'cable 6m',
        df['text'][2] == 'screwdriver 3mm'
    ])
    assert matches >= 2

def test_ai_enum():
    """
    Test AI extract with an enum defined
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - extract.ai:
              model: gpt-4o
              api_key: ${OPENAI_API_KEY}
              seed: 1
              timeout: 60
              retries: 2
              output:
                sentiment:
                  type: string
                  description: >-
                    Describe the sentiment of the text
                  enum:
                    - positive
                    - negative
        """,
        dataframe=pd.DataFrame({
            "data": [
                "The best movie I've ever seen!",
                "I almost threw up. I wouldn't go again.",
                "I had a smile on my face all day."
            ],
        })
    )
    # This is temperamental
    # Score as 2/3 as good enough for test to pass
    matches = sum([
        df["sentiment"][0] == "positive",
        df["sentiment"][1] == "negative",
        df["sentiment"][2] == "positive"
    ])
    assert matches >= 2

def test_ai_timeout():
    df = wrangles.recipe.run(
        """
        wrangles:
          - extract.ai:
              api_key: ${OPENAI_API_KEY}
              seed: 1
              timeout: 0.1
              retries: 0
              output:
                length:
                  type: string
                  description: >-
                    Any lengths found in the data
                    such as cm, m, ft, etc.
        """,
        dataframe=pd.DataFrame({
            "data": [
                "wrench 25mm",
                "6m cable",
                "screwdriver 3mm"
            ],
        })
    )
    assert (
        df['length'][0] == 'Timed Out' and
        df['length'][1] == 'Timed Out' and
        df['length'][2] == 'Timed Out'
    )

def test_ai_timeout_multiple_output():
    """
    Test AI extract with multiple outputs
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - extract.ai:
              model: gpt-4o
              api_key: ${OPENAI_API_KEY}
              seed: 1
              timeout: 0.1
              retries: 0
              output:
                length:
                  type: string
                  description: >-
                    Any lengths found in the data
                    such as cm, m, ft, etc.
                type:
                  type: string
                  description: >-
                    The type of item in the data
                    such as spanner, cellphone, etc.
        """,
        dataframe=pd.DataFrame({
            "data": [
                "wrench 25mm",
                "6m cable",
                "screwdriver 3mm"
            ],
        })
    )
    assert (
        df['length'][0] == 'Timed Out' and
        df['length'][1] == 'Timed Out' and
        df['length'][2] == 'Timed Out' and
        df['type'][0] == 'Timed Out' and
        df['type'][1] == 'Timed Out' and
        df['type'][2] == 'Timed Out'
    )

def test_ai_messages():
    """
    Test openai extract with a header level prompt
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - extract.ai:
              model: gpt-4o
              api_key: ${OPENAI_API_KEY}
              seed: 1
              timeout: 60
              retries: 2
              output:
                length:
                  type: string
                  description: >-
                    Any lengths found in the data
                    such as cm, m, ft, etc.
              messages: All response text should be in upper case.
        """,
        dataframe=pd.DataFrame({
            "data": [
                "wrench 25mm",
                "6m cable",
                "screwdriver 3mm"
            ],
        })
    )

    # This is temperamental, and sometimes GPT returns lowercase
    # Score as 2/3 as good enough for test to pass
    matches = sum([
        df['length'][0] == '25MM',
        df['length'][1] == '6M',
        df['length'][2] == '3MM'
    ])
    assert matches >= 2

def test_ai_array_no_items():
    """
    Test openai extract with array but items type is
    not specified. Defaults to string
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - extract.ai:
              model: gpt-4o
              api_key: ${OPENAI_API_KEY}
              seed: 1
              timeout: 60
              retries: 2
              output:
                fruits:
                  type: array
                  description: >-
                    Return the names of any fruits
                    that are yellow
        """,
        dataframe=pd.DataFrame({
            "data": ["I had 3 strawberries, 5 bananas and 2 lemons"],
        })
    )
    assert (
        ("lemon" in df['fruits'][0] or "lemons" in df['fruits'][0]) and
        ("banana" in df['fruits'][0] or "bananas" in df['fruits'][0])
    )

def test_ai_array_item_type_specified():
    """
    Test openai extract with array where
    the items type is specified
    """
    df = wrangles.recipe.run(
        """
        wrangles:
          - extract.ai:
              model: gpt-4o
              api_key: ${OPENAI_API_KEY}
              seed: 1
              timeout: 60
              retries: 2
              output:
                count:
                  type: array
                  items:
                    type: integer
                  description: >-
                    Get all numbers from the input
        """,
        dataframe=pd.DataFrame({
            "data": ["I had 3 strawberries, 5 bananas and 2 lemons"],
        })
    )
    assert df['count'][0] == [3,5,2]

def test_ai_bad_schema():
    """
    Test that an appropriate error is returned
    if the schema is not valid
    """
    with pytest.raises(ValueError) as error:
        raise wrangles.recipe.run(
            """
            wrangles:
            - extract.ai:
                api_key: ${OPENAI_API_KEY}
                seed: 1
                timeout: 60
                retries: 2
                output:
                  length:
                    type: invalid
                    description: >-
                        Any lengths found in the data
                        such as cm, m, ft, etc.
            """,
            dataframe=pd.DataFrame({
                "data": ["wrench 25mm"],
            })
        )
    assert "schema submitted for output is not valid" in error.value.args[0]

def test_ai_invalid_apikey():
    """
    Test that an appropriate error is returned
    if the api key is invalid
    """
    with pytest.raises(ValueError) as error:
        raise wrangles.recipe.run(
            """
            wrangles:
            - extract.ai:
                api_key: abc123
                seed: 1
                timeout: 60
                retries: 2
                output:
                  length:
                    type: invalid
                    description: >-
                        Any lengths found in the data
                        such as cm, m, ft, etc.
            """,
            dataframe=pd.DataFrame({
                "data": ["wrench 25mm"],
            })
        )
    assert "API Key" in error.value.args[0]

def test_ai_where():
    """
    Test using where with extract.ai
    """
    df = wrangles.recipe.run(
        """
        wrangles:
        - extract.ai:
            input: data
            api_key: ${OPENAI_API_KEY}
            seed: 1
            timeout: 60
            retries: 2
            output:
              length:
                type: integer
                description: Get the number from the input
            where: data LIKE 'wrench%'
        """,
        dataframe=pd.DataFrame({
            "data": ["wrench 25", "spanner 15", "wrench 35", "wrench 45"],
        })
    )
    assert (
        df['length'][1] == "" and (
            df['length'][0] == 25 or
            df['length'][2] == 35 or
            df['length'][3] == 45
        )
    )
