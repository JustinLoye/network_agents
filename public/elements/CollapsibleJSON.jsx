export default function JsonViewer() {
    // `props` is injected globally by Chainlit
    const data = props.data;
  
    // Recursively render keys
    const renderNode = (node, name) => {
      if (
        node === null ||
        typeof node === "string" ||
        typeof node === "number" ||
        typeof node === "boolean"
      ) {
        return (
          <div className="ml-4">
            <strong>{name}:</strong> {String(node)}
          </div>
        );
      }
  
      if (Array.isArray(node)) {
        return (
          <details className="ml-2" open={false}>
            <summary>
              <strong>{name}</strong> [Array({node.length})]
            </summary>
            {node.map((item, i) => (
              <div key={i}>{renderNode(item, i)}</div>
            ))}
          </details>
        );
      }
  
      // object
      return (
        <details className="ml-2" open={false}>
          <summary>
            <strong>{name}</strong> &#123;&#125;
          </summary>
          {Object.entries(node).map(([key, val]) => (
            <div key={key}>{renderNode(val, key)}</div>
          ))}
        </details>
      );
    };
  
    return (
      <div className="font-mono text-sm">
        {renderNode(data, "root")}
      </div>
    );
  }
