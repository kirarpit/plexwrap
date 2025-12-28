import React from "react";
import { motion } from "framer-motion";
import { WrapData } from "../api";

interface LandingPageProps {
  wrapData: WrapData;
  onStartStory: () => void;
}

const LandingPage: React.FC<LandingPageProps> = ({
  wrapData,
  onStartStory,
}) => {
  const user = wrapData.user;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="landing-page"
    >
      <div className="landing-content">
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="landing-header"
        >
          <div className="landing-logo-wrapper">
            <img 
              src={`${process.env.PUBLIC_URL}/logo.png`} 
              alt="Plex Wrapped Logo" 
              className="landing-logo"
            />
          </div>
          <h1>Plex Wrapped</h1>
          <p>Your personalized year in review</p>
        </motion.div>

        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="landing-user-card"
        >
          {user.thumb && (
            <div className="landing-avatar">
              <img src={user.thumb} alt={user.username} />
            </div>
          )}
          <h2>{user.title || user.username}</h2>
          <p className="landing-subtitle">Ready to see your story?</p>
        </motion.div>

        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.6 }}
        >
          <button
            className="landing-start-button"
            onClick={onStartStory}
            aria-label="Start your wrap story"
          >
            View Your Wrap
          </button>
        </motion.div>
      </div>
    </motion.div>
  );
};

export default LandingPage;
