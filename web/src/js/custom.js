var API_GET_WHITELIST = "/whitelist";
var API_SERVICES = "/settings/service";
var API_CRUD_WHITELIST = "/whitelist/entry/";
var API_EXECLOG = "/execution/";

// Init Vue instance
var app = new Vue({
  el: "#app",
  data: {
    whitelist: [],
    settings: [],
    serviceList: [],
    resourceList: [],
    resourceIDPlaceholder: "",
    showWhitelistPopup: false,
    showWhitelistLoadingGIF: false,
    showExecutionLogLoadingGIF: false,

    selectedService: "",
    selectedResource: "",
    selectedResourceID: "",
    selectedOwner: "",
    selectedComment: "",
    selectedExpiration: 0,

    executionLogList: [],
    executionLogTable: [],
    executionLogKey: "",
    executionLogMode: false,
    show_execution_log: false,
  },
  methods: {
    // Whitelist
    closeWhitelistInsertPopup: function () {
      this.showWhitelistPopup = false;
      this.resourceIDPlaceholder = "";
      this.resourceList = [];
      this.selectedComment = "";
      this.selectedExpiration = 0;
      this.selectedOwner = "";
      this.selectedResource = "";
      this.selectedResourceID = "";
      this.selectedService = "";
    },
    createWhitelistEntry: function () {
      let form_data = {
        resource_id:
          this.selectedService +
          ":" +
          this.selectedResource +
          ":" +
          this.selectedResourceID,
        owner: this.selectedOwner,
        comment: this.selectedComment,
      };

      form_url = convert_json_to_get(form_data);
      send_api_request(form_url, "POST");
    },
    deleteWhitelistEntry: function (resource_id) {
      let form_data = {
        resource_id: resource_id,
      };
      form_url = convert_json_to_get(form_data);
      send_api_request(form_url, "DELETE");
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
      this.resourceIDPlaceholder = this.settings[service][resource]["id"];
    },
    updateResourceList: function (service) {
      this.resourceList = Object.keys(this.settings[service]);
      this.resourceIDPlaceholder = "";
    },
    openWhitelistInsertPopup: function () {
      this.showWhitelistPopup = true;
      this.resourceIDPlaceholder = "";
    },
    // Execution Log
    openExecutionLog: function (key_url) {
      get_execution_log(key_url);
    },
    closeExecutionLogPopup: function () {
      $("#executionLogTable").DataTable().destroy();
      this.show_execution_log = false;
    },
  },
});

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
      refresh_whitelist();
      app.closeWhitelistInsertPopup();

      iziToast.show({
        message: data.message,
        color: "#3FBF61",
        messageColor: "white",
      });
    })
    .catch((error) => {
      iziToast.show({
        message:
          "The request has failed. Please see console log for more info.",
        color: "#EC2B55",
        messageColor: "white",
      });
      console.error("Error Submitting Form:", error);
    });
}

// Get execution log for a single instance
function get_execution_log(execlog_url) {
  fetch(API_EXECLOG + execlog_url)
    .then((response) => response.json())
    .then((data) => {
      app.executionLogTable = data["response"]["body"];
      app.executionLogKey = decodeURIComponent(execlog_url);

      if (data["response"]["body"][0][7] == "True") {
        app.executionLogMode = "Dry Run";
      } else {
        app.executionLogMode = "Destroy";
      }

      setTimeout(function () {
        $("#executionLogTable").DataTable({
          paging: false,
          columnDefs: [
            {
              className: "dt-body-nowrap",
              targets: [1, 2, 3, 5],
            },
          ],
        });
        app.show_execution_log = true;
      }, 10);
    })
    .catch((error) => {
      console.error("Error API_RESOURCES:", error);
    });
}

// Get execution logs list
function get_executionLogList() {
  app.showExecutionLogLoadingGIF = true;
  fetch(API_EXECLOG)
    .then((response) => response.json())
    .then((data) => {
      app.executionLogList = data["response"]["logs"].map((row) => {
        row["key_escape"] = encodeURIComponent(row["key"]);
        return row;
      });
      setTimeout(function () {
        $("#execution_log_list_table").DataTable({
          columnDefs: [
            { orderable: false, targets: [2] },
            { className: "dt-center", targets: [2] },
          ],
        });
      }, 10);
      app.showExecutionLogLoadingGIF = false;
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
      app.serviceList = Object.keys(data["response"]);
    })
    .catch((error) => {
      console.error("Error API_SERVICES:", error);
    });
}

// Get whitelist
function get_whitelist() {
  app.whitelist = [];
  app.showWhitelistLoadingGIF = true;
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
          columnDefs: [
            { orderable: false, targets: [3, 4, 5] },
            { className: "dt-center", targets: [4, 5] },
            {
              className: "dt-body-nowrap",
              targets: [0, 1, 2],
            },
          ],
        });
      }, 10);

      app.showWhitelistLoadingGIF = false;
    })
    .catch((error) => {
      console.error("Error API_GET_WHITELIST:", error);
    });
}

function refresh_whitelist() {
  fetch(API_GET_WHITELIST)
    .then((response) => response.json())
    .then((data) => {
      let i = 1;
      let whitelist_raw = data["response"]["whitelist"];
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
    })
    .catch((error) => {
      console.error("Error API_GET_WHITELIST:", error);
    });
}

// Get the API Gateway Base URL from manifest file
fetch("serverless.manifest.json").then(function (response) {
  response.json().then(function (data) {
    var API_BASE = data["prod"]["urls"]["apiGatewayBaseURL"];

    API_GET_WHITELIST = API_BASE + API_GET_WHITELIST;
    API_SERVICES = API_BASE + API_SERVICES;
    API_CRUD_WHITELIST = API_BASE + API_CRUD_WHITELIST;
    API_EXECLOG = API_BASE + API_EXECLOG;

    get_whitelist();
    get_executionLogList();
    get_settings();
  });
});
