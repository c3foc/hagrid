const highlight = '#F3F2FF'
const background = '#0F000A'
const primary = '#FF5053'
const accent1 = '#B2AAFF'
const accent2 = '#6A5FDB'
const accent3 = '#261A66'
const accent4 = '#29114C'
const accent5 = '#190B2F'

const red = primary;
const yellow = '#FFEB50'
const green = '#5FDD6E'
const stateColors = [red, yellow, green]

document.addEventListener('DOMContentLoaded', () => {
  const {remainingStock, saleRate, now, downtimes, availabilities} = JSON.parse(document.getElementById('chart_data').textContent)

  Highcharts.theme = {
    colors: ['#058DC7', '#50B432', '#ED561B', '#DDDF00', '#24CBE5', '#64E572', '#FF9655', '#FFF263', '#6AF9C4'],
    chart: {
      backgroundColor: background,
      color: highlight,
      animation: false,
    },
    title: {text: undefined, style: {color: highlight}},
    subtitle: {style: {color: highlight}},
    yAxis: {
      title: {style: {color: highlight}},
      labels: {style: {color: highlight}},
    },
    xAxis: {
      labels: {style: {color: highlight}},
    },
    legend: {
      itemStyle: {
        font: '9pt Trebuchet MS, Verdana, sans-serif',
        color: 'black',
      },
      itemHoverStyle: {
        color: 'gray',
      },
    },
    plotOptions: {
      area: {
        animation: false,
      },
      column: {
        borderWidth: 0,
      },
      series: {
        animation: false,
      },
    },
  }
  // Apply the theme
  Highcharts.setOptions(Highcharts.theme)

  const plotLines = [
        ...downtimes.map((x) => ({
          color: accent2,
          dashStyle: 'longdash',
          value: x,
          width: 1,
        })),
        {
          color: accent1,
          dashStyle: 'dot',
          value: now,
          width: 1,
          label: {
            text: 'now',
            style: {color: accent1},
            verticalAlign: 'top',
            textAlign: 'left',
          },
        },
      ]

  Highcharts.chart('sale_rate_chart_container', {
    chart: {
      type: 'line',
      plotBorderColor: accent3,
      plotBorderWidth: 1,
    },
    xAxis: {
      allowDecimals: false,
      tickInterval: 3600,
      labels: {
        formatter() {
          return (this.value / 3600).toFixed(0) + 'h'
        },
      },
      plotLines,
    },
    yAxis: [
      {
        id: 'stock',
        title: {
          text: 'Remaining stock',
        },
      },
      {
        id: 'rate',
        opposite: true,
        title: {
          text: 'Sales per hour',
        },
      },
    ],
    legend: {
      enabled: false,
    },
    plotOptions: {
      line: {
        pointStart: 1940,
        marker: {
          enabled: false,
          symbol: 'circle',
          radius: 2,
          states: {
            hover: {
              enabled: true,
            },
          },
        },
      },
    },
    series: [
      {
        name: 'Remaining stock',
        data: remainingStock,
        color: primary,
        yAxis: 'stock',
      },
      {
        name: 'Sale rate',
        data: saleRate,
        color: accent2,
        opacity: 0.7,
        yAxis: 'rate',
        type: 'column',
        pointInterval: 3600,
        pointRange: 3600,
        pointPlacement: 'between',
      },
    ],
  })

  Highcharts.chart('availability_chart_container', {
    chart: {
      type: 'xrange',
      height: availabilities.length * 10+30,
      animation: false,
    },
    legend: {enabled: false},
    xAxis: {
      allowDecimals: false,
      tickInterval: 3600,
      labels: {
        formatter() {
          return (this.value / 3600).toFixed(0) + 'h'
        },
      },
      plotLines,
    },
    yAxis: {
      categories: availabilities.map(a => a.variation),
      reverse: true,
      labels: {
        style: {fontSize: 8},
        allowOverlap: true,
        step: 1,
      },
      tickInterval: 1,
      tickAmount: availabilities.length,

    },
    series: [{
      name: 'Availability',
      pointPadding: 0,
      groupPadding: 0,
      borderWidth: 0,
      pointWidth: 10,
      borderRadius: 0,
      animation: false,
      data: availabilities.flatMap(({variation, timeline}) =>
        timeline.map(({x, x2, y, v}) => ({x, x2, y, color: stateColors[v]})),
      ),
      dataLabels: {
        enabled: true,
      },
    }],
  })
})
