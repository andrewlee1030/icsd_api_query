import requests
import xmltodict
import numpy as np
import datetime
import os
import zipfile
import io
import glob


class icsd_swagger():

	def __init__(self,loginid,password,auth_token = None):
		self.url = 'https://icsd.fiz-karlsruhe.de/ws'
		self.loginid = loginid
		self.loginpass = password

		if os.path.isdir('downloads') == False:
			os.mkdir('downloads')

		self.login(auth_token)

	def login(self, auth_token = None):

		if auth_token != None:
			self.auth_token = auth_token
			print('Authentication token manually specified...')
			return None

		try:
			# read in old authentication key if it exists
			f = open('ICSD-AUTH-TOKEN','r')
			text = f.readlines()[0][:-2] # removes \n from new line
			self.auth_time = text.split(',')[1]
			auth_token = text.split(',')[0]

			# first check if authentication time less than 57 minutes ago (1 hour is the actual limit but it'll be nice to have a buffer)
			auth_time = datetime.datetime.strptime(self.auth_time,'%Y-%m-%d %H:%M:%S.%f')
			now = datetime.datetime.now()
			delta = now - auth_time

			if delta.seconds > 57*60: new_login = True
			else: new_login = False


		except:
			new_login = True
			pass

		if new_login == False:
			self.auth_token = auth_token
			print('Using old authentication token...')
		else:
			error = False
			current_time = datetime.datetime.now()
			self.login_response = requests.post(self.url + '/auth/login', data = {'loginid': self.loginid,'password': self.loginpass})
			
			try:
				self.auth_token = self.login_response.headers['ICSD-Auth-Token']
			except:
				error = True

			if self.login_response.status_code == 200:
				print('Successfully generated new authentication token...')
				f = open('ICSD-AUTH-TOKEN','w+')

				f.write(f'{self.auth_token},{current_time}')
				f.close()
			else:
				error = True

			if error: raise ValueError('Authentication Error (make sure credentials are entered correctly and that all other sessions are closed)')

	def logout(self):
		self.logout_response = requests.get(self.url + '/auth/logout', headers = {'ICSD-Auth-Token': self.auth_token})
		if self.logout_response.status_code == 200:
			print('Logout sucessful.')
			os.remove('ICSD-AUTH-TOKEN')
		else:
			raise ValueError('Error encountered with logout')	

	def simple_search(self,query_text):
		self.simple_search_result = requests.post(self.url + '/search/simple',data = {'query':query_text},headers={'ICSD-Auth-Token':self.auth_token})
		self.query = query_text
		result = self.simple_search_result.content

		if self.simple_search_result.status_code == 401:
			raise ValueError('Simple search failed: Authentication Error')
		elif self.simple_search_result.status_code == 200:
			print(f'Simple search "{query_text}" executed successfully...')
			result_string = xmltodict.parse(result)['hits']['idnums']
			if result_string == None:
				raise ValueError('Search returned zero results.')
			else:
				self.id_nums = result_string.split(' ')
				print(f'{len(self.id_nums)} results found.')

	def expert_search(self,query_text):
		self.expert_search_result = requests.post(self.url + '/search/expert',data = {'query':query_text},headers={'ICSD-Auth-Token':self.auth_token})
		self.query = query_text
		result = self.expert_search_result.content

		if self.expert_search_result.status_code == 401:
			raise ValueError('Expert search failed: Authentication Error')
		elif self.expert_search_result.status_code == 200:
			print(f'Expert search "{query_text}" executed successfully...')
			result_string = xmltodict.parse(result)['hits']['idnums']
			if result_string == None:
				raise ValueError('Search returned zero results.')
			else:
				self.id_nums = result_string.split(' ')
				print(f'{len(self.id_nums)} results found.')

	def custom_coll_codes(self,coll_codes):
		try:
			assert(len(coll_codes) > 0)
			self.id_nums = coll_codes
			print('Set custom array of collection codes successfully.')
		except:
			raise ValueError('Custom collection codes are invalid, make sure you input an array of integers!')

	def download_batch_cifs(self,id_nums,cell_type='experimental',filename = 'CustomDownload',filetype='zip'):
		'''
		DO NOT CALL THIS FUNCTION DIRECTLY! USE 'download_cifs' INSTEAD
		This is just to help the 'download_cifs' function which should work for lists of id numbers of all sizes

		Query parameters
			idnum: array of strings of entry id numbers (remember, numbers must be strings, not ints or floats) ** REQUIRED **
			celltype: string, can be 'experimental' or 'standardized' ; the cell data to use
			filename: string ; custom filename for downloading cifs
			filetype: string, can be 'cif' or 'zip' ; data can be writen to a single cif file or a compressed folder of individual cif files (not sure why you'd ever want the 'cif' option)
		'''
		download = requests.get(self.url + '/cif/multiple', params={'idnum':id_nums,'cell_type':cell_type,'filename':filename,'filetype':filetype}, headers={'ICSD-Auth-Token':self.auth_token},stream=True)
		download_status_code = download.status_code
		if download_status_code == 200:
			with open(f'downloads/{filename}.zip','wb') as f:
				for chunk in download.iter_content(chunk_size=1024):
					f.write(chunk)
			f.close()
			print('Download successful.')

		elif download_status_code == 401: 
			raise ValueError("Not authorized! Authentication token expired or invalid.")

	def download_cifs(self):
		# you must perform one of the '*_search' functions first to get ids
		# ICSD can only download 500 cifs at a time, with a max of 1000 cifs per session
		n_id_nums = len(self.id_nums)

		if n_id_nums == 0: 
			raise ValueError('No entry IDs found for download.')

		n_splits = int(np.ceil(n_id_nums/500))

		id_sublists = np.array_split(np.array(self.id_nums),n_splits)

		total_download_counter = 0
		session_download_counter = 0 # remember that a login session only allows for 1000 cif downloads
		sublist_counter = 0

		for sublist in id_sublists:
			n_sublist = len(sublist)
			session_download_counter += n_sublist
			total_download_counter += n_sublist

			print(f'Downloading {total_download_counter}/{n_id_nums}.')

			if session_download_counter > 1000:
				session_download_counter = n_sublist
				self.logout()
				self.login()

			self.download_batch_cifs(id_nums = sublist,filename = f'{self.query}_{sublist_counter}')
			sublist_counter += 1

	def unzip_downloads(self,destination=None):
		zips = glob.glob('downloads/*')

		for zip_file in zips:
			with zipfile.ZipFile(zip_file, 'r') as zip_ref:
				if destination == None:
					destination = 'unzipped_cifs'
				else:
					pass
				zip_ref.extractall(destination)

