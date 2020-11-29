import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = '1U4B5U0FHRdFC2JV1M0-4z-gUlOE-qq85GJ7hpgJkN5k'
SAMPLE_RANGE_NAME = 'ship_builds!B2:W1000'

creds = None
# The file token.pickle stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.pickle'):
	with open('token.pickle', 'rb') as token:
		creds = pickle.load(token)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
	if creds and creds.expired and creds.refresh_token:
		creds.refresh(Request())
	else:
		flow = InstalledAppFlow.from_client_secrets_file(
			'credentials.json', SCOPES)
		creds = flow.run_local_server(port=0)
	# Save the credentials for the next run
	with open('token.pickle', 'wb') as token:
		pickle.dump(creds, token)
		
service = build('sheets', 'v4', credentials=creds)

# Call the Sheets API
sheet = service.spreadsheets()
result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
							range=SAMPLE_RANGE_NAME).execute()
values = result.get('values', [])
print(dir(result), dir(sheet))

BUILD_BATTLE_TYPE_CLAN = 0
BUILD_BATTLE_TYPE_CASUAL = 1
BUILD_CREATE_BUILD_IMAGES = True
build_battle_type = {
	BUILD_BATTLE_TYPE_CLAN   : "competitive",
	BUILD_BATTLE_TYPE_CASUAL : "casual",
}
build_battle_type_value = {
	"competitive"	: BUILD_BATTLE_TYPE_CLAN,
	"casual" 		: BUILD_BATTLE_TYPE_CASUAL,
}
build = {build_battle_type[BUILD_BATTLE_TYPE_CLAN]:{}, build_battle_type[BUILD_BATTLE_TYPE_CASUAL]:{}}
if not values:
	print('No data found.')
else:
	for row in values:
		build_type = row[1]
		ship_name = row[0]
		upgrades = [i for i in row[2:7] if len(i) > 0]
		skills = [i for i in row[8:-2] if len(i) > 0]
		cmdr = row[-1]
		print(build_type, ship_name, upgrades, skills, cmdr)
		build[build_type][ship_name] = {"upgrades":upgrades, "skills":skills, "cmdr":cmdr}