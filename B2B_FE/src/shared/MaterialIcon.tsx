interface MaterialIconProps {
  name: string;
  className?: string;
}

function MaterialIcon({ name, className = "" }: MaterialIconProps) {
  return (
    <span
      className={`material-symbols-outlined select-none leading-none ${className}`}
      aria-hidden="true"
    >
      {name}
    </span>
  );
}

export default MaterialIcon;
