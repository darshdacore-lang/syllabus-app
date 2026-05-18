const childProcess = require("child_process");
const path = require("path");

module.exports = async function (context) {
    const appOutDir = context.appOutDir;
    if (!appOutDir) {
        return;
    }

    const dest = path.resolve(appOutDir);
    console.log("afterPack cleaning xattrs for:", dest);

    try {
        childProcess.execSync(`find "${dest}" -exec xattr -d com.apple.provenance {} +`, {
            stdio: "inherit",
            shell: true,
        });
    } catch (error) {
        // ignore if the attribute is not present
    }

    try {
        childProcess.execSync(`find "${dest}" -exec xattr -d com.apple.FinderInfo {} +`, {
            stdio: "inherit",
            shell: true,
        });
    } catch (error) {
        // ignore if the attribute is not present
    }

    try {
        childProcess.execSync(`xattr -rc "${dest}"`, {
            stdio: "inherit",
            shell: true,
        });
    } catch (error) {
        // ignore if some files do not support xattr cleanup
    }
};
