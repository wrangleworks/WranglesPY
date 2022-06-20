import wrangles
import os


recipe = "temp.wrgl.yaml"
config = {
    'user': os.environ.get('mongo_user'),
    'password': os.environ.get('mongo_password'),
    'database': 'sample_guides',
    'collection': 'planets',
    'host': 'cluster0.om0uczo.mongodb.net',
    'query': '{"name": "Mars"}',
    'projection': '{"_id": 0}'
}
df = wrangles.pipeline.run(recipe, config)
print(df.to_markdown(index=False))

# recipe2 = """
# read:
#     - mongodb:
#         user: ${user}
#         password: ${password}
#         database: ${database}
#         collection: ${collection}
#         cluster: ${cluster}
#         query: ${query}
#         projection: ${projection}
# wrangles:
#     - convert.case:
#         input: position
#         output: position_caps
#         case: upper
# """
# config2 = {
#     'user': os.environ.get('mongo_user'),
#     'password': os.environ.get('mongo_password'),
#     'database': 'test_db',
#     'collection': 'test_collection',
#     'cluster': 'cluster0.om0uczo.mongodb.net',
#     'query': '{"name": "Fey"}',
#     'projection': '{"_id": 0, "name": 1, "position": 1}'
# }
# df2 = wrangles.pipeline.run(recipe2, config2)
# print(df2)
