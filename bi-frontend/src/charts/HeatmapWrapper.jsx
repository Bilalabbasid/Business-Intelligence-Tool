import React from 'react';

const HeatmapWrapper = ({ title = 'Heatmap', children, height = 320 }) => {
  return (
    <div className="heatmap-wrapper card p-4" style={{ height }}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium">{title}</h3>
      </div>
      <div className="overflow-auto h-full">{children}</div>
    </div>
  );
};

export default HeatmapWrapper;
