#
#

import sublime, sublime_plugin, os, codecs, re, subprocess
import os.path as path


class CtagsFuncComplete(sublime_plugin.EventListener):

	settings_time = 0
	ctags_time = 0
	func_regex  = re.compile("/\^([^\$]+)\$/;\"\s+f")
	prev_pos = 0
	ctags = []

	def load_settings(self):
		# Only load the settings if they have changed
		settings_modified_time = path.getmtime(sublime.packages_path()+"/CtagsFuncComplete/"+"CtagsFuncComplete.sublime-settings")
		if (self.settings_time == settings_modified_time):
			return
		
		self.settings_time = settings_modified_time
		# Variable $project_base_path in settings will be replaced by sublime's project path
		settings = sublime.load_settings("CtagsFuncComplete.sublime-settings")
		
		project_path=""
		if sublime.active_window().project_data() is not None:
			project_path = (sublime.active_window().project_data().get("folders")[0].get("path"))

		self.ctags_file       = settings.get("ctags_file")
		self.ctags_file       = re.sub("(\$project_base_path)", project_path, self.ctags_file)
		self.func_triggers    = settings.get("func_triggers")
		func_complete         = settings.get("active")
		self.syntax           = settings.get("syntax")
		if func_complete == "false":
			self.func_complete = False
		else:
			self.func_complete = True

	def load_ctags(self, file):
		# Load all ctags lines that match the function format
		f = codecs.open(file, encoding='utf-8')
		for line in f:
			tag = re.findall(self.func_regex, line)
			if len(tag) <= 0:
				continue
			self.ctags.append(tag[0])
	
	def on_modified_async(self, view):
		pos = view.sel()[0].begin()
		body = view.substr(sublime.Region(0, view.size()))

		self.load_settings()

		# Only trigger the snippet suggestion when the trigger character is being added
		old_pos = self.prev_pos
		self.prev_pos = pos
		if pos <= old_pos:
			return
		
		# Check if current syntax is allowed first
		if any(view.settings().get('syntax') in s for s in self.syntax) == False:
			return
		# Verify that character under the cursor is one allowed selector
		if self.func_complete == False or any(e in body[pos-1:pos] for e in self.func_triggers) == False:
			return
		if body[pos:pos+1] != ")":
			return
		
		# Only load the tags in the ctags file if it has changed
		ctags_modified_time = path.getmtime(self.ctags_file)
		if (self.ctags_time != ctags_modified_time):
			self.ctags_time = ctags_modified_time
			self.load_ctags(self.ctags_file)

		# Find the function name to look for
		f_end = 0
		f_start = 0
		for i in range (pos, 0, -1):
			char = body[pos]
			if re.match(r'\w+$', char):
				if f_end == 0:
					f_end = pos
				else:
					f_start = pos
			elif f_end != 0:
				break
			pos = pos -1
		self.insert_suggestions(view, body[f_start:f_end+1])

	def insert_suggestions(self, view, fname):
		results = []
		# Find the function definitions that share the provided name
		for tag in self.ctags:
			if re.match("[\s\S]*[:\w]*("+fname+")\s*\(", tag):
				results.append(tag)

		# Format all results in a single string to push to the output panel
		single_res = ""
		for tag in results:
			single_res += tag + "\n"
		if len(results) <= 0:
			return
		
		# Filter only the parameter from the function definition
		params = single_res.split('(')[1]
		params = params.split(')')[0]
		params = params.split(',')
		param_snippet = ""

		# Prepare the snippet string to send to sublime
		i = 1
		for param in params:
			if i > 1:
				param_snippet+= ", "
			param_snippet += "${%d:%s}" % (i, param)
			i+=1

		view.run_command("insert_snippet", { "contents" : param_snippet})
