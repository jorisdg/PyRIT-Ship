https://learn.microsoft.com/en-us/microsoft-edge/extensions/

https://learn.microsoft.com/en-us/microsoft-edge/extensions/getting-started/extension-sideloading


on mouse enter for selected types of elements, we wrap a DIV around it that shows at z-index 1000 (overlay, assuming things aren't over 1000)
the div gets on mouse leave, on click and target data (the control we originally hovered over)
if mouse leaves the div, we remove it from wrapping the original element (other mouse events were on the overlaying DIV so no need to remove anything else explicitly on the target control)
if user clicks, the target is chosen

the issue is that we use IDs for the targeted elements, but many of the elements we see being used don't have a unique ID