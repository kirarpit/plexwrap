import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import "./App.css";
import {
  getUsers,
  getWrap,
  getWrapByToken,
  getTokenForUser,
  User,
  WrapData,
} from "./api";
import UserSelector from "./components/UserSelector";
import WrapDisplay from "./components/WrapDisplay";
import LandingPage from "./components/LandingPage";

function App() {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [wrapData, setWrapData] = useState<WrapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingWrap, setLoadingWrap] = useState(false);
  const [shareToken, setShareToken] = useState<string | null>(null);
  const [showStory, setShowStory] = useState(false);
  const [displayMode, setDisplayMode] = useState<"img" | "html">("html");

  // Sync display mode with URL parameter and available images
  // Priority: explicit URL param > auto-detect (prefer images if available)
  useEffect(() => {
    if (!wrapData) return;

    const urlParams = new URLSearchParams(window.location.search);
    const modeParam = urlParams.get("mode");
    const hasImages =
      wrapData.cards?.some((card) => card.generated_image) ?? false;

    if (modeParam === "img" && hasImages) {
      // Explicit img mode requested and images available
      setDisplayMode("img");
    } else if (modeParam === "html") {
      // Explicit html mode requested
      setDisplayMode("html");
    } else if (modeParam === "img" && !hasImages) {
      // Requested img mode but no images - fall back to html and clean URL
      setDisplayMode("html");
      const token = shareToken || urlParams.get("token");
      if (token) {
        const pathMatch =
          window.location.pathname.match(/^\/w\/([a-f0-9-]+)$/i);
        const currentToken = pathMatch ? pathMatch[1] : token;
        window.history.replaceState({}, "", `/w/${currentToken}`);
      }
    } else {
      // No mode param specified - auto-detect: prefer images if available
      setDisplayMode(hasImages ? "img" : "html");
    }
  }, [wrapData, shareToken]);

  useEffect(() => {
    // Check for token in URL - support both query param (?token=...) and path (/w/token)
    const urlParams = new URLSearchParams(window.location.search);
    let token = urlParams.get("token");

    // Check for display mode parameter
    const mode = urlParams.get("mode");
    if (mode === "img" || mode === "html") {
      setDisplayMode(mode);
    }

    // Also check for /w/{token} path format
    if (!token) {
      const pathMatch = window.location.pathname.match(/^\/w\/([a-f0-9-]+)$/i);
      if (pathMatch) {
        token = pathMatch[1];
        // Keep the path format, don't convert to query param
        // This prevents double tokens
      }
    } else {
      // If token is in query param, convert to path format for cleaner URL
      const pathMatch = window.location.pathname.match(/^\/w\/([a-f0-9-]+)$/i);
      if (!pathMatch || pathMatch[1] !== token) {
        // Preserve mode parameter if present
        const modeParam = urlParams.get("mode");
        const newUrl =
          modeParam && (modeParam === "img" || modeParam === "html")
            ? `/w/${token}?mode=${modeParam}`
            : `/w/${token}`;
        window.history.replaceState({}, "", newUrl);
      }
    }

    if (token) {
      // Load wrap by token
      loadWrapByToken(token);
    } else {
      // Token is required - show error instead of user selector
      setLoading(false);
      setError(
        "A shareable token is required to access wraps. Please use a valid share link."
      );
    }
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const userList = await getUsers();
      setUsers(userList);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load users");
    } finally {
      setLoading(false);
    }
  };

  const loadWrapByToken = async (token: string) => {
    try {
      setLoading(true);
      setLoadingWrap(true);
      setError(null);

      const data = await getWrapByToken(token);
      setWrapData(data);

      // Set a dummy user object for display purposes
      setSelectedUser({
        id: data.user.id,
        username: data.user.username,
        title: data.user.title,
        thumb: data.user.thumb,
      });

      setShareToken(token);
      setShowStory(false); // Start with landing page
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail ||
        err.message ||
        "Failed to load wrap. The token may be invalid.";
      console.error("Error loading wrap by token:", err);
      console.error("Token used:", token);
      console.error(
        "API Base URL:",
        process.env.REACT_APP_API_URL || "auto-detected"
      );
      setError(errorMessage);
      setWrapData(null);
    } finally {
      setLoading(false);
      setLoadingWrap(false);
    }
  };

  const handleUserSelect = async (user: User) => {
    setSelectedUser(user);
    setLoadingWrap(true);
    setError(null);
    setShareToken(null); // Reset token when selecting new user

    try {
      const data = await getWrap(user.username);
      setWrapData(data);

      // Fetch token and update URL
      try {
        const tokenData = await getTokenForUser(user.username);
        setShareToken(tokenData.token);
        // Update URL with shorter format: /w/{token}, preserve mode if present
        const urlParams = new URLSearchParams(window.location.search);
        const modeParam = urlParams.get("mode");
        const newUrl =
          modeParam && (modeParam === "img" || modeParam === "html")
            ? `/w/${tokenData.token}?mode=${modeParam}`
            : `/w/${tokenData.token}`;
        window.history.replaceState({}, "", newUrl);
      } catch (tokenErr) {
        console.error("Failed to fetch token:", tokenErr);
        // Continue without token - wrap will still work
      }
    } catch (err: any) {
      setError(err.message || "Failed to generate wrap");
      setWrapData(null);
    } finally {
      setLoadingWrap(false);
    }
  };

  const handleBack = () => {
    // Don't allow going back - token is required
    // Just reload the page with the token if it exists
    const urlParams = new URLSearchParams(window.location.search);
    let token = urlParams.get("token");

    // Also check for /w/{token} path format
    if (!token) {
      const pathMatch = window.location.pathname.match(/^\/w\/([a-f0-9-]+)$/i);
      if (pathMatch) {
        token = pathMatch[1];
      }
    }

    if (token) {
      // Reload with clean path format, preserve mode parameter if present
      const modeParam = urlParams.get("mode");
      const newUrl =
        modeParam && (modeParam === "img" || modeParam === "html")
          ? `/w/${token}?mode=${modeParam}`
          : `/w/${token}`;
      window.location.href = newUrl;
    } else {
      setError(
        "A shareable token is required to access wraps. Please use a valid share link."
      );
      setSelectedUser(null);
      setWrapData(null);
      setShareToken(null);
    }
  };

  if (loading) {
    return (
      <div className="App">
        <div className="container">
          <div className="loading">Loading...</div>
        </div>
      </div>
    );
  }

  // Only show header when there's an error (not showing LandingPage or WrapDisplay)
  const showHeader = error && !selectedUser && !wrapData;

  return (
    <div className="App">
      <div className="container">
        {showHeader && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="header"
          >
            <div className="header-logo-wrapper">
              <img
                src={`${process.env.PUBLIC_URL}/logo.png`}
                alt="Plex Wrapped Logo"
                className="header-logo"
              />
            </div>
            <h1>Plex Wrapped</h1>
            <p>Your personalized year in review</p>
          </motion.div>
        )}

        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="error"
          >
            {error}
          </motion.div>
        )}

        <AnimatePresence mode="wait">
          {selectedUser && wrapData && !error && !showStory ? (
            <LandingPage
              key="landing"
              wrapData={wrapData}
              onStartStory={() => setShowStory(true)}
            />
          ) : selectedUser && wrapData && !error && showStory ? (
            <WrapDisplay
              key="story"
              wrapData={wrapData}
              loading={loadingWrap}
              onBack={() => setShowStory(false)}
              username={selectedUser.username}
              shareToken={shareToken}
              displayMode={displayMode}
            />
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default App;
