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
		self.error_log = 'Error id nums: \n'

		if os.path.isdir('downloads') == False:
			os.mkdir('downloads')

		self.login(auth_token)

	def login(self, auth_token = None):

		if auth_token != None:
			self.auth_token = auth_token
			print('Authentication token manually specified...')
			return None

		try: # read in old authentication key if it exists
			f = open('ICSD-AUTH-TOKEN','r')
			text = f.readlines()[0][:-2] # removes \n from new line
			self.auth_time = text.split(',')[1]
			auth_token = text.split(',')[0]

			# first check if authentication time less than 57 minutes ago (1 hour is the actual limit but it'll be nice to have a buffer)
			auth_time = datetime.datetime.strptime(self.auth_time,'%Y-%m-%d %H:%M:%S.%f')
			now = datetime.datetime.now()
			delta = now - auth_time

			if delta.seconds > 57*60: new_login = True # authentication key exists but it's too old
			else: new_login = False # authentication key exists and is valid

		except: # start a new login in the absence of an authentication key
			new_login = True
			pass



		if new_login == False: # use old authentication token
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
			self.query = 'custom_coll_codes'
			print('Set custom array of collection codes successfully.')
		except:
			raise ValueError('Custom collection codes are invalid, make sure you input an array of strings of integers!')

	def download_batch_cifs(self,id_nums,sublist_counter, cell_type='experimental',filename = 'CustomDownload',filetype='zip',error_handling='ignore',simple_filenames = True):
		'''
		DO NOT CALL THIS FUNCTION DIRECTLY! USE 'download_cifs' INSTEAD
		This is just to help the 'download_cifs' function which should work for lists of id numbers of all sizes

		Query parameters
			idnum: array of strings of entry id numbers (remember, numbers must be strings, not ints or floats) ** REQUIRED **
			celltype: string, can be 'experimental' or 'standardized' ; the cell data to use
			filename: string ; custom filename for downloading cifs
			filetype: string, can be 'cif' or 'zip' ; data can be writen to a single cif file or a compressed folder of individual cif files (not sure why you'd ever want the 'cif' option)
		'''
		if simple_filenames == True: cif_filename = ''
		else: cif_filename = filename
		download = requests.get(self.url + '/cif/multiple', params={'idnum':id_nums,'cell_type':cell_type,'filename':cif_filename,'filetype':filetype}, headers={'ICSD-Auth-Token':self.auth_token},stream=True)
		download_status_code = download.status_code
		if download_status_code == 200:
			with open(f'downloads/{sublist_counter}{filename}.zip','wb') as f:
				for chunk in download.iter_content(chunk_size=1024):
					f.write(chunk)
			f.close()
			print('Download successful.')
		elif download_status_code == 401: 
			raise ValueError("Error code 401 - Not authorized! Authentication token expired or invalid.")
		elif download_status_code == 500:
			if error_handling != 'ignore': raise ValueError("Error code 500 - The server returned an error. Not exactly sure what happened...")
			else:
				print('Invalid id number(s) detected - attempting to continue, check error output for bad id numbers.')

				# split id nums array in half 

				if len(id_nums) > 1:
					sub_sublists = np.array_split(id_nums,2)
					for i in range(len(sub_sublists)):
						sub_sublist = sub_sublists[i]
						filename += f'_{i}'
						self.download_batch_cifs(id_nums = sub_sublist,filename = filename, sublist_counter = sublist_counter)
				else: # record to error log
					self.error_log = self.error_log + id_nums[0] + '\n'

		elif download_status_code == 403:
			raise ValueError("Error code 403 - There is an issue with authentication. Please log out manually and retry.")
		else:
			raise ValueError(f'ERROR: download status code is {download_status_code}. Please google this up!')
			

	def download_cifs(self, simple_filenames=True):
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
		print(f'There are {len(id_sublists)} sublists to download.')
		for sublist in id_sublists:
			n_sublist = len(sublist)
			session_download_counter += n_sublist
			total_download_counter += n_sublist

			print(f'Downloading sublist {sublist_counter}.')

			if session_download_counter > 1000:
				session_download_counter = n_sublist
				self.logout()
				self.login()

			if simple_filenames == False: filename = f'_{self.query}'
			else: filename = ''
			self.download_batch_cifs(id_nums = sublist,filename = filename,sublist_counter = sublist_counter)
			sublist_counter += 1

		# write the error log
		error_log_file = open('error_log.txt','w+')
		error_log_file.write(self.error_log)
		error_log_file.close()

	def unzip_downloads(self,destination=None):
		zips = glob.glob('downloads/*')

		for zip_file in zips:
			with zipfile.ZipFile(zip_file, 'r') as zip_ref:
				if destination == None:
					destination = 'unzipped_cifs'
				else:
					pass
				zip_ref.extractall(destination)

