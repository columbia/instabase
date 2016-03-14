var WS_SCHEME = "ws://";
var WS_URL = WS_SCHEME + location.host + "/receive";

// plot charts
function plotCharts(scores) {
    var ctx = document.getElementById("trend").getContext("2d");
    var ranks = [];
    var histogram = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
    for (var i = 1; i <= scores.length; i++) {
      ranks.push(i);
      var index = parseInt(scores[i-1] / 10);
      histogram[index] += 1;
      scores[i-1] = scores[i-1].toFixed(2);
    }
    var data = {
        labels: ranks,
        datasets: [
            {
                label: "My first dataset",
                fillColor: "rgba(220,220,220,0.2)",
                strokeColor: "rgba(220,220,220,1)",
                pointColor: "rgba(220,220,220,1)",
                pointStrokeColor: "#fff",
                pointHighlightFill: "#fff",
                pointHighlightStroke: "rgba(220,220,220,1)",
                data: scores
            }
        ]
    };
    var myNewChart = new Chart(ctx).Line(data, {
        "showTooltips": false
    });

    var histodata = {
        labels: ["0-10", "10-20", "20-30", "30-40", "40-50", "50-60", "60-70", "70-80", "80-90", "90-100"],
        datasets: [
            {
                label: "My first dataset",
                fillColor: "rgba(220,220,220,0.2)",
                strokeColor: "rgba(220,220,220,1)",
                pointColor: "rgba(220,220,220,1)",
                pointStrokeColor: "#fff",
                pointHighlightFill: "#fff",
                pointHighlightStroke: "rgba(220,220,220,1)",
                data: histogram
            }
        ]
    }
    var ctx2 = document.getElementById("histo").getContext("2d");
    var myhistochart = new Chart(ctx2).Bar(histodata);
}

function startTracking() {
    // initialize a websocket connection 
    this.inbox = new ReconnectingWebSocket(WS_URL);

    this.inbox.onclose = function() {
        console.log("inbox closed");
        this.inbox = new WebSocket(inbox.url);
    }

    this.inbox.onmessage = function(message) {
        var msg = JSON.parse(message.data);
        if (msg.type === "INFO") {
            console.info("connected");
        }
        if (msg.type === "UPDATE") {
            $('#tracker-msg').slideDown(300);
        }
    }
}

// getting it running
plotCharts(data);
startTracking();
