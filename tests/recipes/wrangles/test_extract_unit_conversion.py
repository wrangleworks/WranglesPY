import pandas as pd
import wrangles
import pytest


#
# misc
#

def test_no_unit():
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
              desired_unit: newtown
        """,
        dataframe=data
    )
    assert df['out'].tolist() == [[], [], [], []]
    
def test_no_unit_object():
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
              desired_unit: newtown
              responseContent: object
        """,
        dataframe=data
    )
    assert df['out'].tolist() == [[], [], [], []]
    
    
def test_non_existing_unit():
    """
    Test a desired unit that does not exists, should return error
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
    assert info.typename == 'ValueError' and info.value.args[0] == 'ERROR IN WRANGLE #1 extract.attributes - Status Code: 400 - Bad Request. {"ValueError":"Invalid desiredUnit provided"}\n \n'

def test_wrong_match_1():
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
    
def test_wrong_match_2():
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
    
def test_very_similar_units():
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
    assert df['out'].tolist() == [['10.9 sq m'], ['2.42 sq m'], ['0.839 sq m'], ['13 sq m']]
    

def test_area_conversion_2():
    """
    Testing multiple units of area object
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
              responseContent: object
        """,
        dataframe=data
    )
    assert df['out'][0] == [{'span': '13 sqr yard', 'standard': '10.9 sq m', 'symbol': 'sq m', 'unit': 'square metre', 'value': 10.9}]
    

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
    assert df['out'][0] == [{'span': '1300 amps', 'standard': '1.3 kA', 'symbol': 'kA', 'unit': 'kiloampere', 'value': 1.3}]
    

def test_current_conversion_2_obj():
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
    
    
def test_multile_forces_2():
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
    assert df['out'].tolist() == [['1 kW'], ['1 kW'], ['10 kW'], ['1 kW'], ['0.746 kW']]
    
    
def test_power_conversion_2_obj():
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
    assert df['out'].tolist() == [['1 kPa'], ['1 kPa'], ['10 kPa'], ['1 kPa'], ['100 kPa'], ['6.89 kPa'], ['0.133 kPa']]
    
def test_pressure_conversion_2_obj():
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
    

def test_temperature_conversion_2_obj():
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
    assert df['out'].tolist() == [['379 l'], ['1 l'], ['100 l'], ['100 l'], ['379 l'], ['100 l']]
    
def test_volume_conversion_2_obj():
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
    assert df['out'].tolist() == [['2.64 gpm'], ['10 gpm'], ['74.8 gpm'], ['2.64 gpm']]
    
def test_volumetric_flow_rate_conversion_2_obj():
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
    assert df['out'].tolist() == [['0.621 mi'], ['0.621 mi'], ['0.0621 mi'], ['0.0158 mi'], ['0.568 mi'], ['1 mi'], ['0.932 mi'], ['0.189 mi']]
    
def test_length_conversion_2_obj():
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
    assert [{'span': '1000 meters', 'standard': '0.621 mi', 'symbol': 'mi', 'unit': 'mile', 'value': 0.621}]
    
    
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
    assert df['out'].tolist() == [['220 lb'], ['100 lb'], ['100 lb'], ['100 lb'], ['2.2 lb'], ['22 lb'], ['220 lb'], ['0.22 lb']]
    
def test_weight_conversion_2_obj():
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
    
    
def test_voltage_conversion_1():
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
    
def test_voltage_conversion_2_obj():
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

def test_degree_conversion_1():
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
    
def test_degree_conversion_2():
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
    assert [{'span': '1000 radian', 'standard': '57300°', 'symbol': '°', 'unit': 'degree angle', 'value': 57300}]
    
        

#
# Capacitance
#

def test_capacitance_conversion_1():
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
    
def test_capacitance_conversion_2_obj():
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


def test_frequency_conversion_1():
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
    
def test_frequency_conversion_2_obj():
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
    assert df['out'][3] == [{'symbol': 'kHz', 'unit': 'kilohertz', 'value': 100.0}]


#
# Speed/Velocity
#

def test_speed_conversion_1():
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
    
def test_speed_conversion_2_obj():
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

def test_charge_conversion_1():
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
    
def test_charge_conversion_2_obj():
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


def test_data_transfer_rate_conversion_1():
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
    
def test_data_transfer_rate_conversion_2_obj():
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


def test_electrical_conductance_conversion_1():
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
    
def test_electrical_conductance_conversion_2_obj():
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


def test_inductance_conversion_1():
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
    
def test_inductance_conversion_2_obj():
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


def test_frequency_conversion_2():
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
    
def test_frequency_conversion_2_obj():
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


def test_lumens_conversion_1():
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
    
def test_lumens_conversion_2_obj():
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

def test_ohms_conversion_1():
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
    
def test_ohms_conversion_2_obj():
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

def test_energy_conversion_1():
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
    
def test_energy_conversion_2_obj():
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
# Emtpy Dataframe test
#

def test_empty_conversion():
    """
    Test empty dataframe
    """
    data = pd.DataFrame(
        {'col': []}
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
    assert df.empty and df.columns.to_list() == ['col', 'out']