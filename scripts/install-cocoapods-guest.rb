require 'rubygems'
require 'rubygems/package'
require 'rubygems/installer'
require 'json'

project = '/Volumes/SystemRoot/workspace'
lock = JSON.parse(File.read(project+'/config/cocoapods-gems.lock.json'))
cache = project+'/runtime/gem-offline-cache/'
json_gem = lock['gems'].find {|item| item['name']=='json'}
abort 'Bundled JSON version does not match the lock' unless JSON::VERSION == json_gem['version']
spec = Gem::Package.new(cache+json_gem['file']).spec
spec.extensions = []
File.write(File.join(Gem.default_specifications_dir, spec.spec_name), spec.to_ruby)
Gem::Specification.reset

lock['gems'].each do |item|
  next if item['name']=='json'
  installed = Gem::Specification.find_all_by_name(item['name'], item['version']).any? {|s| s.platform.to_s == item['platform']}
  next if installed
  Gem::Installer.at(cache+item['file'], :ignore_dependencies=>true, :document=>[]).install
  puts 'Installed '+item['file']
end
puts 'CocoaPods Darwin gems installed from the verified lock.'
