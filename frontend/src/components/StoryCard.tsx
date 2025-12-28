import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CardDeckItem } from "../types/cards";
import { getPosterUrls } from "../utils/imageUtils";

interface StoryCardProps {
  card: CardDeckItem;
  direction: number;
  posterUrls?: string[];
  displayMode?: "img" | "html";
}

const slideVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? window.innerWidth : -window.innerWidth,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction: number) => ({
    x: direction > 0 ? -window.innerWidth : window.innerWidth,
    opacity: 0,
  }),
};

export const StoryCard: React.FC<StoryCardProps> = ({
  card,
  direction,
  posterUrls = [],
  displayMode = "html",
}) => {
  const [backgroundUrls, setBackgroundUrls] = useState<string[]>([]);
  const [imagesLoaded, setImagesLoaded] = useState(false);
  const [generatedImageUrl, setGeneratedImageUrl] = useState<string | null>(
    null
  );
  const [generatedImageLoaded, setGeneratedImageLoaded] = useState(false);

  // Check if card has a generated image
  const hasGeneratedImage =
    card.generatedImage !== null && card.generatedImage !== undefined;

  // Load generated image only if displayMode is 'img'
  useEffect(() => {
    // Only fetch generated images when in 'img' mode
    if (displayMode !== "img") {
      setGeneratedImageLoaded(true);
      return;
    }

    if (hasGeneratedImage && card.generatedImage) {
      // Convert relative path to full URL
      // If it's already a full URL, use it directly
      let imageUrl = card.generatedImage;
      if (!imageUrl.startsWith("http://") && !imageUrl.startsWith("https://")) {
        // It's a relative path, construct full URL
        const port = typeof window !== "undefined" ? window.location.port : "";
        const hostname =
          typeof window !== "undefined"
            ? window.location.hostname
            : "localhost";

        // Determine API base URL (same logic as api.ts and imageUtils.ts)
        let apiBaseUrl = "";
        // Development ports - need absolute URL to backend
        const devPorts = ["3000", "5173", "5174", "4200"];
        
        if (devPorts.includes(port)) {
          // For development, use absolute URL to backend
          apiBaseUrl = `http://${hostname}:8000`;
        } else {
          // For all other cases (Docker/nginx on any port), use relative URLs
          // nginx will proxy /api/* requests to the backend
          apiBaseUrl = "";
        }

        // First, get the image modification time for cache-busting
        const imagePath = encodeURIComponent(card.generatedImage);
        fetch(`${apiBaseUrl}/api/generated-image-info?path=${imagePath}`)
          .then((res) => (res.ok ? res.json() : null))
          .then((info) => {
            // Add modification time as query parameter for cache-busting
            const cacheBuster = info?.mtime ? `&t=${info.mtime}` : "";
            const finalImageUrl = `${apiBaseUrl}/api/generated-image?path=${imagePath}${cacheBuster}`;

            // Preload generated image
            const img = new Image();
            img.onload = () => {
              setGeneratedImageUrl(finalImageUrl);
              setGeneratedImageLoaded(true);
            };
            img.onerror = () => {
              console.warn("Failed to load generated image:", finalImageUrl);
              setGeneratedImageLoaded(true); // Still mark as loaded to show fallback
            };
            img.src = finalImageUrl;
          })
          .catch((err) => {
            console.warn(
              "Failed to get image info, loading without cache-busting:",
              err
            );
            // Fallback: load without cache-busting
            const fallbackUrl = `${apiBaseUrl}/api/generated-image?path=${imagePath}`;
            const img = new Image();
            img.onload = () => {
              setGeneratedImageUrl(fallbackUrl);
              setGeneratedImageLoaded(true);
            };
            img.onerror = () => {
              console.warn("Failed to load generated image:", fallbackUrl);
              setGeneratedImageLoaded(true);
            };
            img.src = fallbackUrl;
          });
      } else {
        // Already a full URL, use directly
        const img = new Image();
        img.onload = () => {
          setGeneratedImageUrl(imageUrl);
          setGeneratedImageLoaded(true);
        };
        img.onerror = () => {
          console.warn("Failed to load generated image:", imageUrl);
          setGeneratedImageLoaded(true);
        };
        img.src = imageUrl;
      }
    } else {
      setGeneratedImageLoaded(true);
    }
  }, [hasGeneratedImage, card.generatedImage, displayMode]);

  // Load poster URLs for background images (always in HTML mode, or when no generated image in images mode)
  useEffect(() => {
    // In HTML mode, always load background images regardless of generated image availability
    // In img mode, only load background images if there's no generated image
    if (displayMode === "img" && hasGeneratedImage) {
      setImagesLoaded(true);
      return;
    }

    if (posterUrls && posterUrls.length > 0) {
      getPosterUrls(posterUrls).then((urls) => {
        if (urls.length > 0) {
          // Preload all images before showing them to avoid pop-in
          const imagePromises = urls.map((url) => {
            return new Promise<void>((resolve) => {
              const img = new Image();
              img.onload = () => resolve();
              img.onerror = () => resolve(); // Resolve even on error to not block
              img.src = url;
            });
          });

          Promise.all(imagePromises).then(() => {
            setBackgroundUrls(urls);
            setImagesLoaded(true);
          });
        } else {
          setImagesLoaded(true);
        }
      });
    } else {
      setImagesLoaded(true);
    }
  }, [posterUrls, hasGeneratedImage, displayMode]);

  const hasBackground = backgroundUrls.length > 0 && imagesLoaded;
  const isCollage = backgroundUrls.length > 1;

  // If we have a generated image AND display mode is 'img', show it instead of the UI
  // Only show images if explicitly requested via displayMode='img'
  const showGeneratedImage =
    displayMode === "img" &&
    hasGeneratedImage &&
    generatedImageUrl &&
    generatedImageLoaded;

  return (
    <AnimatePresence mode="popLayout" custom={direction} initial={false}>
      <motion.div
        key={card.id}
        custom={direction}
        variants={slideVariants}
        initial="enter"
        animate="center"
        exit="exit"
        transition={{
          x: {
            type: "spring",
            stiffness: 500,
            damping: 50,
            mass: 0.5,
          },
          opacity: {
            duration: 0.2,
            ease: [0.4, 0, 0.2, 1],
          },
        }}
        style={{
          willChange: "transform",
          overflow: "hidden",
        }}
        className={`story-card ${hasBackground ? "has-background" : ""} ${
          isCollage ? "has-collage" : ""
        } ${showGeneratedImage ? "has-generated-image" : ""}`}
      >
        {/* Generated image mode - show image instead of UI */}
        {showGeneratedImage ? (
          <div className="story-card-generated-image-container">
            <img
              src={generatedImageUrl}
              alt={card.title}
              className="story-card-generated-image"
            />
          </div>
        ) : (
          <>
            {/* Background layer */}
            {hasBackground && (
              <div className="story-card-background">
                {isCollage ? (
                  <div
                    className={`story-card-collage collage-${Math.min(
                      backgroundUrls.length,
                      6
                    )}`}
                  >
                    {backgroundUrls.slice(0, 6).map((url, index) => (
                      <div
                        key={index}
                        className="collage-item"
                        style={{
                          backgroundImage: `url(${url})`,
                        }}
                      />
                    ))}
                  </div>
                ) : (
                  <div
                    className="story-card-poster"
                    style={{
                      backgroundImage: `url(${backgroundUrls[0]})`,
                    }}
                  />
                )}
                <div className="story-card-background-overlay" />
              </div>
            )}

            <div
              className="story-card-header"
              style={card.color ? { borderTopColor: card.color } : {}}
            >
              {card.icon && (
                <span className="story-card-emoji">{card.icon}</span>
              )}
              <h2 className="story-card-title">{card.title}</h2>
              {card.subtitle && (
                <p className="story-card-subtitle">{card.subtitle}</p>
              )}
            </div>
            <div className="story-card-body">{card.content}</div>
          </>
        )}
      </motion.div>
    </AnimatePresence>
  );
};
