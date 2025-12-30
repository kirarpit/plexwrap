import React, { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { WrapData, getTokenForUser } from "../api";
import { buildCardDeck } from "./cards/CardFactory";
import { useSwipe } from "../hooks/useSwipe";
import { StoryCard } from "./StoryCard";

interface NavAreaProps {
  side: "left" | "right";
  onClick: () => void;
  disabled: boolean;
  "aria-label": string;
}

// Component to handle tap vs scroll detection
const NavArea: React.FC<NavAreaProps> = ({
  side,
  onClick,
  disabled,
  "aria-label": ariaLabel,
}) => {
  const touchStartRef = useRef<{ x: number; y: number; time: number } | null>(
    null
  );
  const touchHandledRef = useRef<boolean>(false);
  const [isActive, setIsActive] = useState(false);

  const handleTouchStart = (e: React.TouchEvent) => {
    if (disabled) return;
    touchHandledRef.current = false;
    const touch = e.touches[0];
    touchStartRef.current = {
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now(),
    };
    setIsActive(true);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!touchStartRef.current) return;
    const touch = e.touches[0];
    const deltaX = Math.abs(touch.clientX - touchStartRef.current.x);
    const deltaY = Math.abs(touch.clientY - touchStartRef.current.y);

    // If vertical movement is significant, cancel the tap and allow scroll
    if (deltaY > 5 && deltaY > deltaX * 0.5) {
      setIsActive(false);
      touchStartRef.current = null;
      // Don't prevent default - allow scrolling
      return;
    }

    // If horizontal movement is significant, prevent default to allow tap
    if (deltaX > 5 && deltaX > deltaY * 2) {
      e.preventDefault();
    }
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (!touchStartRef.current || disabled) {
      setIsActive(false);
      return;
    }

    const touch = e.changedTouches[0];
    const deltaX = Math.abs(touch.clientX - touchStartRef.current.x);
    const deltaY = Math.abs(touch.clientY - touchStartRef.current.y);
    const deltaTime = Date.now() - touchStartRef.current.time;

    // Only trigger if:
    // 1. Movement is mostly horizontal (or very small)
    // 2. Movement is less than 10px (tap, not drag)
    // 3. Time is less than 300ms (quick tap)
    if (deltaX < 10 && deltaY < 10 && deltaTime < 300) {
      touchHandledRef.current = true;
      onClick();
      // Prevent click event from firing after touch
      e.preventDefault();
    } else if (deltaX > deltaY && deltaX > 20 && deltaTime < 500) {
      // Horizontal swipe gesture
      touchHandledRef.current = true;
      onClick();
      // Prevent click event from firing after touch
      e.preventDefault();
    }

    setIsActive(false);
    touchStartRef.current = null;

    // Reset touch handled flag after a delay to allow click events on desktop
    setTimeout(() => {
      touchHandledRef.current = false;
    }, 300);
  };

  const handleClick = (e: React.MouseEvent) => {
    if (disabled) return;
    // Prevent click if we just handled a touch event (mobile)
    if (touchHandledRef.current) {
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    e.preventDefault();
    onClick();
  };

  return (
    <button
      className={`story-nav-area story-nav-area-${side} ${
        isActive ? "active" : ""
      }`}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      onClick={handleClick}
      disabled={disabled}
      aria-label={ariaLabel}
    />
  );
};

interface WrapDisplayProps {
  wrapData: WrapData | null;
  loading: boolean;
  onBack: () => void;
  username: string;
  shareToken?: string | null;
  displayMode?: 'img' | 'html';
}

const WrapDisplay: React.FC<WrapDisplayProps> = ({
  wrapData,
  loading,
  onBack,
  username,
  shareToken: initialShareToken,
  displayMode = 'html',
}) => {
  const [shareToken, setShareToken] = useState<string | null>(
    initialShareToken || null
  );

  // Fetch token if not provided
  useEffect(() => {
    if (!wrapData || loading || shareToken) return;

    const fetchToken = async () => {
      try {
        const tokenData = await getTokenForUser(username);
        setShareToken(tokenData.token);
        // Update URL with shorter format: /w/{token}
        // Preserve mode parameter if present
        const urlParams = new URLSearchParams(window.location.search);
        const modeParam = urlParams.get("mode");
        const newUrl = modeParam && (modeParam === 'img' || modeParam === 'html')
          ? `/w/${tokenData.token}?mode=${modeParam}`
          : `/w/${tokenData.token}`;
        window.history.replaceState({}, "", newUrl);
      } catch (err) {
        console.error("Failed to fetch token:", err);
      }
    };

    fetchToken();
  }, [wrapData, loading, username, shareToken]);

  // Update URL when token is available (use shorter format)
  useEffect(() => {
    if (shareToken) {
      // Preserve mode parameter if present
      const urlParams = new URLSearchParams(window.location.search);
      const modeParam = urlParams.get("mode");
      const newUrl = modeParam && (modeParam === 'img' || modeParam === 'html')
        ? `/w/${shareToken}?mode=${modeParam}`
        : `/w/${shareToken}`;
      const currentPath = window.location.pathname;
      const currentSearch = window.location.search;

      // Only update URL if it's different and doesn't already have the token
      // Check both path format and query param format to avoid duplicates
      const queryToken = new URLSearchParams(currentSearch).get("token");

      // If path doesn't match OR query param exists (causing double token), update to clean path format
      if (currentPath !== newUrl || queryToken) {
        window.history.replaceState({}, "", newUrl);
      }
    }
  }, [shareToken]);

  // Build card deck using factory (empty array if no data)
  // Must be defined before the fullscreen useEffect that depends on it
  const cards = wrapData ? buildCardDeck(wrapData) : [];

  // Enter fullscreen when story mode opens (only if we have cards)
  useEffect(() => {
    if (!wrapData || loading || cards.length === 0) return;

    const enterFullscreen = async () => {
      try {
        const doc = document.documentElement;
        // Try different fullscreen APIs for different browsers
        if (doc.requestFullscreen) {
          await doc.requestFullscreen();
        } else if ((doc as any).webkitRequestFullscreen) {
          // Safari
          await (doc as any).webkitRequestFullscreen();
        } else if ((doc as any).mozRequestFullScreen) {
          // Firefox
          await (doc as any).mozRequestFullScreen();
        } else if ((doc as any).msRequestFullscreen) {
          // IE/Edge
          await (doc as any).msRequestFullscreen();
        }
      } catch (error) {
        // Fullscreen might not be available or user denied
        console.log("Fullscreen not available:", error);
      }
    };

    // Try fullscreen on all devices when story opens
    enterFullscreen();

    // Exit fullscreen when component unmounts
    return () => {
      const exitFullscreen = () => {
        try {
          // Check if we're actually in fullscreen mode
          const isFullscreen =
            document.fullscreenElement ||
            (document as any).webkitFullscreenElement ||
            (document as any).mozFullScreenElement ||
            (document as any).msFullscreenElement;

          if (!isFullscreen) {
            return; // Not in fullscreen, nothing to exit
          }

          if (document.exitFullscreen) {
            document.exitFullscreen().catch(() => {
              // Ignore errors - fullscreen might not be available
            });
          } else if ((document as any).webkitExitFullscreen) {
            (document as any).webkitExitFullscreen();
          } else if ((document as any).mozCancelFullScreen) {
            (document as any).mozCancelFullScreen();
          } else if ((document as any).msExitFullscreen) {
            (document as any).msExitFullscreen();
          }
        } catch (error) {
          // Silently ignore errors - fullscreen might not be available
        }
      };
      exitFullscreen();
    };
  }, [wrapData, loading, cards.length]);

  // Use swipe hook for navigation (must be called before early returns)
  const {
    currentIndex: currentCardIndex,
    direction,
    goToNext,
    goToPrevious,
    goToIndex,
  } = useSwipe({
    totalCards: cards.length,
  });

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="loading"
      >
        Generating your wrap... 🎬
      </motion.div>
    );
  }

  if (!wrapData || cards.length === 0) {
    // Show error message instead of returning null when cards are missing
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="wrap-container story-mode"
        style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          flexDirection: 'column',
          padding: '2rem',
          textAlign: 'center'
        }}
      >
        <button
          className="story-close-button"
          onClick={onBack}
          aria-label="Close"
        >
          ✕
        </button>
        <div style={{ 
          background: 'rgba(0, 0, 0, 0.5)', 
          borderRadius: '20px', 
          padding: '2rem',
          maxWidth: '500px',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255, 255, 255, 0.2)'
        }}>
          <span style={{ fontSize: '4rem', display: 'block', marginBottom: '1rem' }}>📭</span>
          <h2 style={{ marginBottom: '1rem', fontSize: '1.5rem' }}>No Cards Available</h2>
          <p style={{ opacity: 0.9, lineHeight: 1.6 }}>
            {wrapData 
              ? "Your wrap data was found, but no story cards were generated. This might mean the wrap needs to be regenerated with the latest version."
              : "Unable to load wrap data. Please try again or check if the wrap has been generated."
            }
          </p>
          <button
            onClick={onBack}
            style={{
              marginTop: '1.5rem',
              padding: '0.75rem 2rem',
              borderRadius: '25px',
              border: '2px solid rgba(255, 255, 255, 0.4)',
              background: 'rgba(255, 255, 255, 0.1)',
              color: 'white',
              fontSize: '1rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Go Back
          </button>
        </div>
      </motion.div>
    );
  }

  const currentCard = cards[currentCardIndex];

  const handleClose = () => {
    // Exit fullscreen before closing (only if in fullscreen)
    const exitFullscreen = () => {
      try {
        // Check if we're actually in fullscreen mode
        const isFullscreen =
          document.fullscreenElement ||
          (document as any).webkitFullscreenElement ||
          (document as any).mozFullScreenElement ||
          (document as any).msFullscreenElement;

        if (!isFullscreen) {
          return; // Not in fullscreen, nothing to exit
        }

        if (document.exitFullscreen) {
          document.exitFullscreen().catch(() => {
            // Ignore errors - fullscreen might not be available
          });
        } else if ((document as any).webkitExitFullscreen) {
          (document as any).webkitExitFullscreen();
        } else if ((document as any).mozCancelFullScreen) {
          (document as any).mozCancelFullScreen();
        } else if ((document as any).msExitFullscreen) {
          (document as any).msExitFullscreen();
        }
      } catch (error) {
        // Silently ignore errors - fullscreen might not be available
      }
    };
    exitFullscreen();
    onBack();
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="wrap-container story-mode"
    >
      {/* Close button - top right corner */}
      <button
        className="story-close-button"
        onClick={handleClose}
        aria-label="Close"
      >
        ✕
      </button>

      {/* Progress bar at top */}
      <div className="story-progress-container">
        {cards.map((_, index) => (
          <div
            key={index}
            className={`story-progress-segment ${
              index <= currentCardIndex ? "filled" : ""
            }`}
            style={{
              width: `${100 / cards.length}%`,
            }}
          />
        ))}
      </div>

      {/* Card counter */}
      <div className="story-counter">
        {currentCardIndex + 1} / {cards.length}
      </div>

      {/* Card area */}
      <div className="story-card-wrapper">
        <StoryCard
          card={currentCard}
          direction={direction}
          posterUrls={currentCard.posterUrls}
          displayMode={displayMode}
        />
      </div>

      {/* Clickable navigation areas - left and right sides */}
      <div className="story-nav-areas">
        <NavArea
          side="left"
          onClick={goToPrevious}
          disabled={currentCardIndex === 0}
          aria-label="Previous card"
        />
        <NavArea
          side="right"
          onClick={goToNext}
          disabled={currentCardIndex === cards.length - 1}
          aria-label="Next card"
        />
      </div>

      {/* Desktop navigation (hidden on mobile) */}
      <div className="story-desktop-nav">
        <button
          className="story-nav-button"
          onClick={goToPrevious}
          disabled={currentCardIndex === 0}
          aria-label="Previous"
        >
          ←
        </button>
        <div className="story-dots">
          {cards.map((_, index) => (
            <button
              key={index}
              className={`story-dot ${
                index === currentCardIndex ? "active" : ""
              }`}
              onClick={() => goToIndex(index)}
              aria-label={`Go to card ${index + 1}`}
            />
          ))}
        </div>
        <button
          className="story-nav-button"
          onClick={goToNext}
          disabled={currentCardIndex === cards.length - 1}
          aria-label="Next"
        >
          →
        </button>
      </div>
    </motion.div>
  );
};

export default WrapDisplay;
