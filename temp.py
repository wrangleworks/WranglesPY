import wrangles

config_file = 'samples/standardize_test.yml'
params = {
    'inputFile': 'data/standardize_test_sheet.xlsx',
    'outputFile': 'data/output/standardize_test_output.xlsx',
}
wrangles.pipeline.run(config_file, params=params)

