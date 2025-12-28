import { useState, useCallback } from "react";
import { PanInfo } from "framer-motion";

interface UseSwipeOptions {
  totalCards: number;
  onSwipe?: (direction: number) => void;
}

interface UseSwipeReturn {
  currentIndex: number;
  direction: number;
  goToNext: () => void;
  goToPrevious: () => void;
  goToIndex: (index: number) => void;
  handleDragEnd: (
    event: MouseEvent | TouchEvent | PointerEvent,
    info: PanInfo
  ) => void;
  handleDragStart: (
    event: MouseEvent | TouchEvent | PointerEvent,
    info: PanInfo
  ) => void;
  handleDrag: (
    event: MouseEvent | TouchEvent | PointerEvent,
    info: PanInfo
  ) => void;
}

export const useSwipe = ({
  totalCards,
  onSwipe,
}: UseSwipeOptions): UseSwipeReturn => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [direction, setDirection] = useState(0);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(
    null
  );

  const goToNext = useCallback(() => {
    if (currentIndex < totalCards - 1) {
      setDirection(1);
      const newIndex = currentIndex + 1;
      setCurrentIndex(newIndex);
      onSwipe?.(1);
    }
  }, [currentIndex, totalCards, onSwipe]);

  const goToPrevious = useCallback(() => {
    if (currentIndex > 0) {
      setDirection(-1);
      const newIndex = currentIndex - 1;
      setCurrentIndex(newIndex);
      onSwipe?.(-1);
    }
  }, [currentIndex, onSwipe]);

  const goToIndex = useCallback(
    (index: number) => {
      if (index >= 0 && index < totalCards) {
        setDirection(index > currentIndex ? 1 : -1);
        setCurrentIndex(index);
        onSwipe?.(index > currentIndex ? 1 : -1);
      }
    },
    [currentIndex, totalCards, onSwipe]
  );

  const handleDragStart = useCallback(
    (event: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
      setDragStart({ x: info.point.x, y: info.point.y });
    },
    []
  );

  const handleDrag = useCallback(
    (event: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
      const target = event.currentTarget as HTMLElement;
      if (!target || !dragStart) return;

      const deltaY = Math.abs(info.point.y - dragStart.y);
      const deltaX = Math.abs(info.point.x - dragStart.x);

      // If horizontal movement is dominant, disable scrolling temporarily
      // Use requestAnimationFrame to avoid layout thrashing
      if (deltaX > 10 && deltaX > deltaY * 1.2) {
        requestAnimationFrame(() => {
          target.style.overflowY = "hidden";
          target.style.touchAction = "pan-x";
          // Also update body and all child elements to allow horizontal drag
          const body = target.querySelector(".story-card-body") as HTMLElement;
          if (body) {
            body.style.overflowY = "hidden";
            body.style.touchAction = "pan-x";
            body.style.pointerEvents = "none";
          }
          // Disable pointer events on all interactive children during drag
          const interactiveElements = target.querySelectorAll("a, button, input, select, textarea");
          interactiveElements.forEach((el) => {
            (el as HTMLElement).style.pointerEvents = "none";
          });
        });
      }
    },
    [dragStart]
  );

  const handleDragEnd = useCallback(
    (event: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
      const target = event.currentTarget as HTMLElement;
      
      const swipeThreshold = 80; // Reduced threshold for easier swiping
      const swipeVelocity = 250; // Reduced velocity threshold
      const verticalThreshold = 60; // Slightly increased to prevent accidental swipes

      const horizontalMovement = Math.abs(info.offset.x);
      const verticalMovement = Math.abs(info.offset.y);
      const isHorizontalSwipe = horizontalMovement > verticalMovement * 1.5;

      // Restore styles after a brief delay to allow animation to start smoothly
      requestAnimationFrame(() => {
        if (target) {
          target.style.overflowY = "auto";
          target.style.touchAction = "";
          const body = target.querySelector(".story-card-body") as HTMLElement;
          if (body) {
            body.style.overflowY = "auto";
            body.style.touchAction = "";
            body.style.pointerEvents = "";
          }
          // Re-enable pointer events on interactive children
          const interactiveElements = target.querySelectorAll("a, button, input, select, textarea");
          interactiveElements.forEach((el) => {
            (el as HTMLElement).style.pointerEvents = "";
          });
        }
      });

      if (
        isHorizontalSwipe &&
        (horizontalMovement > swipeThreshold ||
          Math.abs(info.velocity.x) > swipeVelocity) &&
        verticalMovement < verticalThreshold
      ) {
        // Use requestAnimationFrame to ensure smooth transition
        requestAnimationFrame(() => {
          if (info.offset.x > 0 || info.velocity.x > 0) {
            // Swipe right - go to previous card
            goToPrevious();
          } else {
            // Swipe left - go to next card
            goToNext();
          }
        });
      }
      // Note: dragSnapToOrigin in StoryCard will handle snap-back automatically

      setDragStart(null);
    },
    [goToNext, goToPrevious]
  );

  return {
    currentIndex,
    direction,
    goToNext,
    goToPrevious,
    goToIndex,
    handleDragEnd,
    handleDragStart,
    handleDrag,
  };
};

