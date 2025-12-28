import React from "react";
import { CardText } from "../../types/cards";
import { formatDuration } from "../../utils/formatters";
import { extractTopDevice, extractOtherDevices } from "../../utils/metricExtractors";

interface DeviceCardProps {
  text: CardText;
  metrics: Record<string, any>;
}

export const DeviceCard: React.FC<DeviceCardProps> = ({ text, metrics }) => {
  const topDevice = extractTopDevice(metrics);
  const otherDevices = extractOtherDevices(metrics);

  return (
    <div className="card-content">
      {text.headline && <h3 className="card-headline">{text.headline}</h3>}
      <p className="card-description">{text.description}</p>
      {topDevice.name && (
        <div className="device-main">
          <div className="device-name">{topDevice.name}</div>
          <div className="device-stats">
            {topDevice.minutes !== null && (
              <div className="device-time">
                {formatDuration(topDevice.minutes)}
              </div>
            )}
            {topDevice.percentage !== null && (
              <div className="device-percentage">
                {topDevice.percentage.toFixed(1)}%
              </div>
            )}
          </div>
        </div>
      )}
      {otherDevices.length > 0 && (
        <div className="device-others">
          <div className="device-others-label">Other devices:</div>
          {otherDevices.map((device, index: number) => (
            <div key={index} className="device-other-item">
              <span className="device-other-name">{device.name}</span>
              <span className="device-other-stats">
                {device.minutes > 0 && formatDuration(device.minutes)}
                {device.minutes > 0 && device.percentage > 0 && " "}
                {device.percentage > 0 && `(${device.percentage.toFixed(1)}%)`}
              </span>
            </div>
          ))}
        </div>
      )}
      {text.aside && <p className="card-aside">{text.aside}</p>}
    </div>
  );
};
