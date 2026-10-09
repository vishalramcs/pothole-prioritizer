"use client";

import { BarElement, CategoryScale, Chart as ChartJS, LinearScale, Tooltip } from "chart.js";
import { Bar } from "react-chartjs-2";
import { cardClass, labelClass } from "@/components/ui/styles";
import { COLORS } from "@/lib/colors";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

/** A bar chart with the same numbers in a table, so values can be read exactly (design brief 6, 8). */
export default function BarWithTable({ title, labels, values, valueLabel, colors = COLORS.ink, horizontal = false }: {
  title: string;
  labels: string[];
  values: number[];
  valueLabel: string;
  colors?: string | string[];
  horizontal?: boolean;
}) {
  return (
    <figure className={`flex flex-col gap-3 ${cardClass}`}>
      <figcaption className="text-xl font-bold">{title}</figcaption>
      {values.length === 0 ? (
        <p className="text-muted">No data yet.</p>
      ) : (
        <>
          <div className="h-48">
            <Bar
              aria-hidden // the table below carries the same data for screen readers
              data={{ labels, datasets: [{ label: valueLabel, data: values, backgroundColor: colors }] }}
              options={{
                indexAxis: horizontal ? "y" : "x",
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { [horizontal ? "x" : "y"]: { beginAtZero: true, ticks: { precision: 0 } } },
              }}
            />
          </div>
          <table className="w-full text-left text-sm">
            <thead className={labelClass}><tr><th></th><th>{valueLabel}</th></tr></thead>
            <tbody>
              {labels.map((l, i) => (
                <tr key={l} className="border-t border-border"><td className="py-0.5">{l}</td><td>{values[i]}</td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </figure>
  );
}
