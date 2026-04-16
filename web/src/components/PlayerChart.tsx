import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  type TooltipItem,
} from "chart.js";
import type { PlayerHistory } from "../types/api";
import { formatNumber } from "../utils/formatting";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
);

interface Props {
  data: PlayerHistory;
}

const MONTH_KEY_REGEX = /^\d{4}-\d{2}$/;

function parseMonthlyData(data: PlayerHistory): {
  labels: string[];
  values: number[];
} {
  const entries: [string, number][] = [];

  for (const [key, value] of Object.entries(data)) {
    if (MONTH_KEY_REGEX.test(key) && typeof value === "number") {
      entries.push([key, value]);
    }
  }

  entries.sort((a, b) => a[0].localeCompare(b[0]));

  return {
    labels: entries.map(([key]) => {
      const [year, month] = key.split("-");
      const date = new Date(Number(year), Number(month) - 1);
      return date.toLocaleDateString("en-US", {
        month: "short",
        year: "numeric",
      });
    }),
    values: entries.map(([, value]) => value),
  };
}

export default function PlayerChart({ data }: Props) {
  const { labels, values } = parseMonthlyData(data);

  if (labels.length === 0) {
    return <div className="chart-empty">No player history data available</div>;
  }

  const chartData = {
    labels,
    datasets: [
      {
        label: "Monthly Players",
        data: values,
        borderColor: "#5865f2",
        backgroundColor: "rgba(88, 101, 242, 0.2)",
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointBackgroundColor: "#5865f2",
        pointBorderColor: "#ffffff",
        pointBorderWidth: 1,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      tooltip: {
        callbacks: {
          label: (ctx: TooltipItem<"line">) => {
            if (ctx.parsed.y == null) return "";
            return formatNumber(ctx.parsed.y);
          },
        },
      },
    },
    scales: {
      x: {
        ticks: { color: "#8f98a0", maxTicksLimit: 12 },
        grid: { color: "#2a2d35" },
      },
      y: {
        ticks: {
          color: "#8f98a0",
          callback: (value: string | number) =>
            formatNumber(Number(value)),
        },
        grid: { color: "#2a2d35" },
      },
    },
  };

  return (
    <div className="chart-section">
      <h2 className="section-title">Player History</h2>
      <div className="chart-container" style={{ height: "300px" }}>
        <Line data={chartData} options={options} />
      </div>
    </div>
  );
}
