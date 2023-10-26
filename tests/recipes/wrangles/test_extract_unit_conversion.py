import pandas as pd
import wrangles

#
# area
#

def test_area_conversion_1():
    """
    Test multiple units of area
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
              attribute_type: area
              desired_unit: square meters
        """,
        dataframe=data
    )
    assert df['out'].tolist() == [['10.9 sq m'], ['2.42 sq m'], ['0.839 sq m'], ['13.0 sq m']]
    

#
# current
#

def test_current_conversion_1():
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
    assert df['out'][0] == [{'symbol': 'kA', 'unit': 'kiloampere', 'value': '1.3'}]
    
    
#
# force
#

def test_multile_forces():
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
    

#
# power
#

def test_power_conversion_1():
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
    assert df['out'].tolist() == [['1.0 kW'], ['1.0 kW'], ['10.0 kW'], ['1.0 kW'], ['0.746 kW']]
    
    
#
# pressure
#

def test_pressure_conversion_1():
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
    assert df['out'].tolist() == [['1.0 kPa'], ['1.0 kPa'], ['10.0 kPa'], ['1.0 kPa'], ['100 kPa'], ['6.89 kPa'], ['0.133 kPa']]
    

#
# temperature
#

def test_temperature_conversion_1():
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


#
# volume
#

def test_volume_conversion_1():
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
    assert df['out'].tolist() == [['379 l'], ['1.0 l'], ['100 l'], ['100 l'], ['379 l'], ['100 l']]
    
#
# volumetric flow rate
#

def test_volumetric_flow_rate_conversion_1():
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
    assert df['out'].tolist() == [['2.64 gpm'], ['10.0 gpm'], ['74.8 gpm'], ['2.64 gpm']]
    
#
# Length
#

def test_length_conversion_1():
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
    assert df['out'].tolist() == [['0.621 mi'], ['0.621 mi'], ['0.0621 mi'], ['0.0158 mi'], ['0.568 mi'], ['1.0 mi'], ['0.932 mi'], ['0.189 mi']]
    
    
#
# weight
#

def test_weight_conversion_1():
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
    assert df['out'].tolist() == [['220 lb'], ['100 lb'], ['100 lb'], ['100 lb'], ['2.2 lb'], ['22.0 lb'], ['220 lb'], ['0.22 lb']]