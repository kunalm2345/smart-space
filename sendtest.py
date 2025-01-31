import vdms
import json
db = vdms.vdms()
db.connect("10.8.1.200", 55555)


blob_arr = []
fd = open("./hi.png","rb")
blob_arr.append(fd.read())

all_queries = []
addImage = {}
# addImage["properties"] = props
# addImage["operations"] = operations
# addImage["link"] = link
addImage["format"] = "png"

# get one image with a particular name
query = {}

# {
#   "FindEntity": {
#     "class": "Image",
#     "constraints": {
#       "name": ["==", "sample_image.jpg"]
#     },
#     "results": 1,
#     "blob": true
#   }
# }

query["AddImage"] = addImage

all_queries.append(query)

print("Query Sent:")
print(all_queries)

response, res_arr = db.query(query=json.dumps(all_queries), blob_array=[blob_arr,])

print("Response:")
print(response, res_arr)
