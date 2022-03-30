import wrangles

config_file = 'temp/conf/test.yml'
params = {
    'inputFile': 'temp/input/ERN AEP TEST.xlsx',
    'outputFile': 'temp/output/test.xlsx',
}
wrangles.pipeline.run(config_file, params=params)


# config_file = 'temp/conf/ern-pur-other.yml'
# params = {
#     'inputFile': 'temp/input/ERN AEP pur.xlsx',
#     'outputFile': 'temp/output/ern-pur-other.xlsx',
# }
# wrangles.pipeline.run(config_file, params=params)