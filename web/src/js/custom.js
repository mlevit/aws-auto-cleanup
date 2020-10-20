var API_GET_WHITELIST = "/whitelist";
var API_SERVICES = "/settings/service";
var API_CRUD_WHITELIST = "/whitelist/entry/";
var API_EXECLOG = "/execution/";

// Get the API Gateway Base URL from manifest file
fetch("serverless.manifest.json")
  .then(function (response) {
    response.json().then(function (data) {
      var API_BASE = data["dev"]["urls"]["apiGatewayBaseURL"];

      API_GET_WHITELIST = API_BASE + API_GET_WHITELIST;
      API_SERVICES = API_BASE + API_SERVICES;
      API_CRUD_WHITELIST = API_BASE + API_CRUD_WHITELIST;
      API_EXECLOG = API_BASE + API_EXECLOG;

      get_whitelist();
      get_execution_log_list();
      get_settings();
    });
  })
  .catch(function (err) {
    console.log(
      "Could not retrieve 'apiGatewayBaseURL' from 'serverless.manifest.json' file."
    );
  });

// Init Vue instance
var app = new Vue({
  el: "#app",
  data: {
    whitelist: [],
    settings: [],
    service_list: [],
    resource_list: [],
    resource_id_placeholder: "",
    show_whitelist_popup: false,
    show_whitelist_loading_gif: false,
    show_execution_log_list_loading_gif: false,

    selected_service: "",
    selected_resource: "",
    selected_resource_id: "",
    selected_owner: "",
    selected_comment: "",
    selected_expiration: 0,

    execution_log_list: [],
    api_execlog_url: API_EXECLOG,

    show_execution_log: false,
    execlog_table: [],
  },
  methods: {
    // Whitelist
    closeWhitelistInsertPopup: function () {
      this.show_whitelist_popup = false;
    },
    createWhitelistEntry: function () {
      let form_data = {
        resource_id:
          this.selected_service +
          ":" +
          this.selected_resource +
          ":" +
          this.selected_resource_id,
        owner: this.selected_owner,
        comment: this.selected_comment,
      };

      form_url = convert_json_to_get(form_data);
      send_api_request(form_url, "POST");
    },
    deleteWhitelistEntry: function (resource_id) {
      if (confirm("Are you sure you would like to delete the entry?")) {
        let form_data = {
          resource_id: resource_id,
        };
        form_url = convert_json_to_get(form_data);
        send_api_request(form_url, "DELETE");
      }
    },
    extendWhitelistEntry: function (row_id) {
      let row = this.whitelist[row_id - 1];
      let form_data = {
        resource_id: row.resource_id,
        expiration: row.expiration,
        owner: row.owner,
        comment: row.comment,
      };

      form_url = convert_json_to_get(form_data);
      send_api_request(form_url, "PUT");
    },
    updateResourceID: function (service, resource) {
      this.resource_id_placeholder = this.settings[service][resource]["id"];
    },
    updateResourceList: function (service) {
      this.resource_list = Object.keys(this.settings[service]);
    },
    openWhitelistInsertPopup: function () {
      this.show_whitelist_popup = true;
      this.resource_id_placeholder = "";
    },
    // Execution Log
    openEXLog: function (key_url) {
      get_execution_log(key_url);
    },
    closeEXpopup: function () {
      this.show_execution_log = false;
    },
  },
});

// Get execution log for a single instance
function get_execution_log(execlog_url) {
  fetch(API_EXECLOG + execlog_url)
    .then((response) => response.json())
    .then((data) => {
      app.execlog_table = data["response"]["body"];
      setTimeout(function () {
        $("#execlog-table").DataTable();
        app.show_execution_log = true;
      }, 1);
    })
    .catch((error) => {
      console.error("Error API_RESOURCES:", error);
    });
}

// Get execution logs list
function get_execution_log_list() {
  app.show_execution_log_list_loading_gif = true;
  fetch(API_EXECLOG)
    .then((response) => response.json())
    .then((data) => {
      app.execution_log_list = data["response"]["logs"].map((row) => {
        row["key_escape"] = encodeURIComponent(row["key"]);
        return row;
      });
      setTimeout(function () {
        $("#execution_log_list_table").DataTable();
      }, 10);
      app.show_execution_log_list_loading_gif = false;
    })
    .catch((error) => {
      console.error("Error API_RESOURCES:", error);
    });
}

// Get settings
function get_settings() {
  fetch(API_SERVICES)
    .then((response) => response.json())
    .then((data) => {
      app.settings = data["response"];
      app.service_list = Object.keys(data["response"]);
    })
    .catch((error) => {
      console.error("Error API_SERVICES:", error);
    });
}

// Get whitelist
function get_whitelist() {
  app.whitelist = [];
  app.show_whitelist_loading_gif = true;
  fetch(API_GET_WHITELIST)
    .then((response) => response.json())
    .then((data) => {
      let i = 1;
      let whitelist_raw = data["response"]["whitelist"];
      // Add row ID for action reference
      app.whitelist = whitelist_raw.map((item) => {
        item["id"] = i++;
        dayjs.extend(dayjs_plugin_utc);
        dayjs.extend(dayjs_plugin_timezone);
        let readable_date = dayjs
          .unix(item["expiration"])
          .tz("Australia/Melbourne");
        item["expiration_readable"] = readable_date.format(
          "ddd MMM DD HH:mm:ss YYYY"
        );
        return item;
      });
      setTimeout(function () {
        $("#whitelist").DataTable({
          columnDefs: [{ orderable: false, targets: [3, 4, 5] }],
        });
      }, 10);
      app.show_whitelist_loading_gif = false;
    })
    .catch((error) => {
      console.error("Error API_GET_WHITELIST:", error);
    });
}

// Utility functions
function convert_json_to_get(form_json) {
  let form_url = "";
  for (var key in form_json) {
    form_url += key + "=" + form_json[key] + "&";
  }
  form_url.substr(0, form_url.length - 1);
  return form_url;
}

function send_api_request(form_url, request_method) {
  fetch(API_CRUD_WHITELIST + "?" + form_url, {
    method: request_method,
  })
    .then((response) => response.json())
    .then((data) => {
      $.notify(data.message, "success");
      get_whitelist();
      get_execution_log_list();
      app.closeWhitelistInsertPopup();
    })
    .catch((error) => {
      $.notify(
        "The request has failed. Please see console log for more info.",
        "error"
      );
      console.error("Error Submitting Form:", error);
    });
}

// get_whitelist();
// get_execution_log_list();
// get_settings();
