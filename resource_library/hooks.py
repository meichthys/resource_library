app_name = "resource_library"
app_title = "Resource Library"
app_publisher = "Meichthys"
app_description = "A resource management app built on the Frappe framework"
app_email = "resource_management@meichthys.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
add_to_apps_screen = [
	{
		"name": "resource_library",
		"logo": "/assets/resource_library/resource_library-logo.svg",
		"title": "Resource Library",
		"route": "/desk/resource-library",
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/resource_library/css/resource_library.css"
# app_include_js = "/assets/resource_library/js/resource_library.js"

# include js, css files in header of web template
# Note: must contain ".bundle." and NOT start with "/assets" for Frappe to
# resolve it through the hashed assets.json manifest (see bundled_asset() in
# frappe/utils/jinja_globals.py) — otherwise it's served with a 1-year
# Cache-Control and browsers never pick up changes.
web_include_css = "resource_library.bundle.css"
# web_include_js = "/assets/resource_library/js/resource_library.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "resource_library/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "resource_library/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
home_page = "resources"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "resource_library.utils.jinja_methods",
# 	"filters": "resource_library.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "resource_library.install.before_install"
after_install = "resource_library.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "resource_library.uninstall.before_uninstall"
# after_uninstall = "resource_library.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "resource_library.utils.before_app_install"
# after_app_install = "resource_library.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "resource_library.utils.before_app_uninstall"
# after_app_uninstall = "resource_library.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "resource_library.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"resource_library.tasks.all"
# 	],
# 	"daily": [
# 		"resource_library.tasks.daily"
# 	],
# 	"hourly": [
# 		"resource_library.tasks.hourly"
# 	],
# 	"weekly": [
# 		"resource_library.tasks.weekly"
# 	],
# 	"monthly": [
# 		"resource_library.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "resource_library.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "resource_library.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "resource_library.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["resource_library.utils.before_request"]
# after_request = ["resource_library.utils.after_request"]

# Job Events
# ----------
# before_job = ["resource_library.utils.before_job"]
# after_job = ["resource_library.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"resource_library.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

